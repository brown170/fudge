# <<BEGIN-copyright>>
# Copyright 2022, Lawrence Livermore National Security, LLC.
# See the top-level COPYRIGHT file for details.
# 
# SPDX-License-Identifier: BSD-3-Clause
# <<END-copyright>>

"""
This module containes all the classes for handling GNDS table instance.

This module contains the following classes:

    +-----------------------------------+-----------------------------------------------------------------------+
    | Class                             | Description                                                           |
    +===================================+=======================================================================+
    | Table                             | This class represents                                                 |
    +-----------------------------------+-----------------------------------------------------------------------+
    | ColumnHeader                      | This class represents                                                 |
    +-----------------------------------+-----------------------------------------------------------------------+
    | Blank                             | This class represents                                                 |
    +-----------------------------------+-----------------------------------------------------------------------+
"""

from . import enums as enumsModule
from LUPY import ancestry as ancestryModule
from pqu import PQU as PQUModule

class Table(ancestryModule.AncestryIO):
    """
    This class defines one column heaader in a :py:class:`Table` instance.

    The following table list the primary members of this class:

    +---------------+---------------------------------------------------------------+
    | Member        | Description                                                   |
    +===============+===============================================================+
    | columns       | The index of the column in the table.                         |
    +---------------+---------------------------------------------------------------+
    | data          | The name for the column.                                      |
    +---------------+---------------------------------------------------------------+
    | storageOrder  | The storage order of the data in the table.                   |
    +---------------+---------------------------------------------------------------+
    """

    moniker = 'table'

    def __init__(self, columns=None, data=None, storageOrder=enumsModule.StorageOrder.rowMajor):

        ancestryModule.AncestryIO.__init__(self)

        storageOrder = enumsModule.StorageOrder.checkEnumOrString(storageOrder)
        if storageOrder != enumsModule.StorageOrder.rowMajor:
            raise ValueError('Currently, only supported value for storageOrder is "%s", got "%s".' % (enumsModule.StorageOrder.rowMajor, storageOrder))
        self.__storageOrder = storageOrder

        self.columns = columns or []

        self.data = data or []
        if not all( [len(d)==self.nColumns for d in self.data] ):
            raise ValueError("Data is the wrong shape for a table with %i columns!" % self.nColumns)

    @property
    def storageOrder(self):
        """
        Returns to value of the storageOrder.
        """

        return self.__storageOrder

    @property
    def nColumns(self):
        """
        This method returns the number of column in the table.
        """

        return len(self.columns)

    @property
    def nRows(self):
        """
        This method returns the number of rows in the table.
        """

        return len(self.data)

    def __len__( self ):
        """
        This method returns the number of rows in the table.
        """

        return self.nRows

    def __getitem__( self, indices ):
        """
        This method returns the contents of a cell of *self* or a slice of *self*.

        :param indices:     A slice of the data to return.

        :returns:           A cells or a slice of the table.
        """

        if type(indices) is int: return self.data[ indices ]
        if len(indices)==2:
            i,j = indices
            if type(i) is slice:
                return [d[j] for d in self.data[i]]
            return self.data[i][j]
        raise IndexError("invalid index")

    def addRow( self, dataRow ):
        """
        This method adds a row to *self*.

        :param dataRow:     The row to add.
        """

        if not len(dataRow) == self.nColumns:
            raise ValueError("New row has %i columns, should have %i!" % (len(dataRow),self.nColumns))
        self.data.append( dataRow )

    def addColumn( self, columnHeader, index=None ):
        """
        This method insert the column *columnHeader* into *self* at *index* or at the end of the table if *index* is None.

        :param columnHeader:    The column to add.
        :param index:           The index of the
        """

        if not isinstance(columnHeader, ColumnHeader):
            raise TypeError("addColumn requires a ColumnHeader instance but got %s" % type(columnHeader))
        if index:
            self.columns.insert(index, columnHeader)
            [row.insert(index, 0) for row in self.data]
        else:
            self.columns.append( columnHeader )
            [row.append(0) for row in self.data]
        for idx, col in enumerate(self.columns): col.index = idx

    def convertUnits( self, unitMap ):
        """
        Converts all data in *self* per *unitMap*.

        :param unitMap:     A dictionary in which each key is a unit that will be replaced by its value which must be an equivalent unit.
        """

        for idx, column in enumerate(self.columns):
            if column.unit in unitMap:
                factor = PQUModule.PQU(1, column.unit).getValueAs(unitMap[column.unit])
                column.unit = unitMap[column.unit]
                for row in self.data:
                    row[idx] *= factor

    def getColumn( self, columnNameOrIndex, unit=None ):
        """This method returns a column of self.

        Convert results to desired unit if specified.

        :param columnNameOrIndex:   This can be an index (python int) or name (str) for the column to return.
        :param unit:                The unit of the returned data.

        :returns:                   A column.
        """

        if isinstance(columnNameOrIndex, int):
            index = columnNameOrIndex
            column = self.columns[index]
        else:
            column = [a for a in self.columns if a.name==columnNameOrIndex]
            if not column: return None
            if len(column) > 1: raise ValueError("Column named '%s' is not unique!" % columnNameOrIndex)
            column = column[0]
            index = self.columns.index( column )
        if unit:
            cf = PQUModule.convertUnits(column.unit, {column.unit: unit})[1]
            return [cf * v for v in self[:,index]]
        return self[:,index]

    def removeColumn( self, columnName ):
        """
        This methods removes a column from *self*.

        :param columnName:  The name of the column to remove.
        """

        column = [a for a in self.columns if a.name==columnName]
        if not column: raise ValueError("column '%s' isn't present in the table!" % columnName)
        if len(column) > 1: raise Exception("Column named '%s' is not unique!" % columnName)
        index = self.columns.index( column[0] )
        self.columns.pop( index )
        [row.pop(index) for row in self.data]
        for idx, col in enumerate(self.columns): col.index = idx

    def toStringList(self, indent='',**kwargs):
        """
        Returns a list of str instances representing the data of *self* as XML lines.

        :param indent:          The minimum amount of indentation.
        :param kwargs:          A dictionary of extra arguments that controls how *self* is converted to a list of XML strings.

        :return:                List of str instances representing the XML lines of *self*'s data.
        """

        addHeader = kwargs.get( 'addHeader', True )
        addHeaderUnit = kwargs.get( 'addHeaderUnit', False )
        outline = kwargs.get( 'outline', False )
        columnWidths = [0] * self.nColumns
        xml = []
        for col in range(self.nColumns):
            columnDat = [row[col] for row in self.data if not isinstance(row[col], Blank)]
            asStrings = list( map( PQUModule.toShortestString, columnDat ) )
            columnWidths[col] = max( list( map( len, asStrings ) ) )

        if addHeader:
            """ put column labels at the top of the table """
            names = [col.name for col in self.columns]
            lengths = [len(name) for name in names]
            if any( [' width' in name for name in names] ):
                # special treatment for RML widths: split up onto two lines
                nameL = [[],[]]
                for name in names:
                    if ' width' in name: l,r = name.split(' width'); r = ' width'+r+' '
                    else: l,r = name, ''
                    nameL[0].append(l); nameL[1].append(r)
                names = nameL
                lengths = [len(name) for name in names[0]]
            else: names = [names]
            columnWidths = [max(columnWidths[i],lengths[i]) for i in range(self.nColumns)]

            header = ['%s<!--' % (' '*(len(indent)-1)) + ' | '.join([('%%%is'%columnWidths[i]) % nameList[i]
                for i in range(self.nColumns)]) + '  -->'   for nameList in names]
            xml += header

        if addHeaderUnit:
            """ put column unit at the top of the table """
            unit = [str(col.unit) for col in self.columns]
            lengths = [len(u) for u in unit]
            columnWidths = [max(columnWidths[i],lengths[i]) for i in range(self.nColumns)]
            header = ['%s<!--' % (' ' * (len(indent) - 1)) + ' | '.join( [('%s'%u).rjust(columnWidths[i]) for i,u in enumerate(unit) ] ) + '  -->']
            xml += header

        template = ['%s' % (indent + ' ')] + ['%%%is' % l for l in columnWidths]

        def toString(val):
            if isinstance(val, Blank): return str(val)
            return PQUModule.toShortestString(val)

        if outline:
            xml += [('   '.join(template) % tuple( map(toString, dataRow))).rstrip() for dataRow in self.data[:3]]
            xml += ['%s ...' % indent]
            xml += [('   '.join(template) % tuple( map(toString, dataRow))).rstrip() for dataRow in self.data[-3:]]
        else:
            xml += [('   '.join(template) % tuple( map(toString, dataRow))).rstrip() for dataRow in self.data]
        return xml

    def toXML_strList(self, indent = '', **kwargs):
        """
        Returns a list of str instances representing the XML lines of *self*.

        :param indent:          The minimum amount of indentation.
        :param kwargs:          A dictionary of extra arguments that controls how *self* is converted to a list of XML strings.

        :return:                List of str instances representing the XML lines of self.
        """

        indent2 = indent + kwargs.get('incrementalIndent', '  ')
        indent3 = indent2 + kwargs.get('incrementalIndent', '  ')
        if len(self.data) < 10: outline = False

        XML_strList = ['%s<%s rows="%i" columns="%i">' % (indent,self.moniker,self.nRows,self.nColumns)]
        XML_strList.append('%s<columnHeaders>' % (indent2))
        for column in self.columns: XML_strList += column.toXML_strList(indent3)
        XML_strList[-1] += '</columnHeaders>'

        if not self.data:
            XML_strList.append('%s<data/></%s>' % (indent2, self.moniker))
            return XML_strList

        XML_strList.append('%s<data>' % (indent2))
        XML_strList += self.toStringList(indent=indent3, **kwargs)
        XML_strList[-1] += '</data></%s>' % self.moniker

        return XML_strList

    @classmethod
    def parseNodeUsingClass(cls, element, xPath, linkData, **kwargs):
        """
        Parse *node* into an instance of *cls*. To convert a column or attribute from string to some other type,
        enter the new type in a dictionary in the key "conversionTable" of *kwargs*. For example::

            kwargs['conversionTable'] = {'index': int, 'scatteringRadius': PhysicalQuantityWithUncertainty}).

        :param cls:         Form class to return.
        :param element:     Node to parse.
        :param xPath:       List containing xPath to current node, useful mostly for debugging.
        :param linkData:    dict that collects unresolved links.
        :param kwargs:      A dictionary of extra arguments that controls how *self* is converted to a list of XML strings.

        :returns:           An instance of *cls* representing *element*.
        """

        xPath.append(element.tag)
        def fixAttributes(items):
            attrs = dict(items)
            for key in attrs:
                if key == 'index': attrs[key] = int(attrs[key])
                if key in conversionTable: attrs[key] = conversionTable[key]( attrs[key] )
            return attrs

        def floatOrBlank(val):
            if val=='_': return Blank()
            return float(val)

        conversionTable = linkData.get('conversionTable',{})
        nRows = int(element.get('rows'))
        nColumns = int(element.get('columns'))
        storageOrder = element.get('storageOrder', enumsModule.StorageOrder.rowMajor)
        if storageOrder != enumsModule.StorageOrder.rowMajor:
            storageOrder = enumsModule.StorageOrder.fromString(storageOrder)

        _columns = element.find('columnHeaders')
        columns = [ ColumnHeader(**fixAttributes(list(column.items()))) for column in _columns ]
        data = element.find('data')

        if data.text:
            data = list(map(floatOrBlank, data.text.split()))
        else:
            data = []
        for i in range(len(columns)):
            if columns[i].name in conversionTable:
                data[i::nColumns] = list(map(conversionTable[columns[i].name], data[i::nColumns]))
        assert len(data) == nRows * nColumns
        data = [data[i*nColumns:(i+1)*nColumns] for i in range(nRows)]

        table = cls(columns, data, storageOrder=storageOrder)

        xPath.pop()

        return table

class ColumnHeader:
    """
    This class defines one column heaader in a :py:class:`Table` instance.

    The following table list the primary members of this class:

    +-----------+---------------------------------------------------------------+
    | Member    | Description                                                   |
    +===========+===============================================================+
    | index     | The index of the column in the table.                         |
    +-----------+---------------------------------------------------------------+
    | name      | The name for the column.                                      |
    +-----------+---------------------------------------------------------------+
    | unit      | The unit for the data for the column.                         |
    +-----------+---------------------------------------------------------------+
    """

    def __init__( self, index, name, unit ):
        """
        :param index:       The index of the column in the table.
        :param name:        The name for the column.
        :param unit:        The unit for the data for the column.
        """

        self.index = index
        self.name = name
        self.unit = unit

    def __str__(self):
        """
        This method returns a simple string representation of *self*.
        """

        return '%s (%s)'%(self.name,self.unit)

    def __eq__(self, other):
        """
        This method returns True if the name and unit of *self* is the same as *other*, and False otherwise.

        :param other:       Another :py:class:`ColumnHeader` instance.
        """

        return self.name == other.name and self.unit == other.unit

    def toXML_strList(self, indent='', **kwargs):
        """
        Returns a list of str instances representing the XML lines of *self*.

        :param indent:          The minimum amount of indentation.
        :param kwargs:          A dictionary of extra arguments that controls how *self* is converted to a list of XML strings.

        :return:                List of str instances representing the XML lines of self.
        """

        return [ '%s<column index="%d" name="%s" unit="%s"/>' % ( indent, self.index, self.name, self.unit ) ]

class Blank:
    """This class represents a blank table entry, to indicate missing data. This class has not members."""

    def __init__( self ): pass
    def __str__( self ): return '_'
    def __add__( self, other ): return self
    def __radd__( self, other ): return self
    def __mul__( self, other ): return self
    def __rmul__( self, other ): return self
