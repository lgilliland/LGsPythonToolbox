
LGs Python Toolbox
==================

## Introduction:
This project contains 3 simple, interactive, and hopefully helpful geoprocessing tools created to serve as an example implementation of a Python toolbox (.pyt) that can be used, for instance, within Esri's ArcCatalog.  Note - The newer Python toolbox is different than the older Custom toolbox.  (i.e. Via ArcCatalog, if you right click on 
a folder and click New..., you can see "Python Toolbox" and "Toolbox".)

Please see this [Esri link](http://pro.arcgis.com/en/pro-app/arcpy/geoprocessing_and_python/a-quick-tour-of-python-toolboxes.htm) for more information on Python toolboxes.

## Environment:
This script was created and tested with python 2.7. The script relies on Esri's Arcpy module, and has been tested with ArcGis Desktop 10.4.1.

## Details: 
All of the python code is contained in the .pyt file.  The .xml files contain related metadata about the toolbox and tools.  Please see below for more info on the tools.

## Usage:
Simply copy the files into a local folder, start ArcCatalog, and browse to the .pyt file.  The 3 tools should show up underneath the LGsPythonToolbox.pyt file.  Double click a tool to launch.

## Tools: 
The following 3 tools are included in this example toolbox.

### 1. Breakup Shapefile Tool: 
This tool takes a shapefile and extracts features from the shapefile to their own, individual shapefile.  For instance, if you have a shapefile containing all of the countries in Africa, and you needed to create a single shapefile for each country.  An optional where clause can be specified to restrict the features to be extracted.  A unique field must be specified as the key field to use when generating the new shapefile name for each extracted feature.  Finally, an output folder for the newly generated shapefile(s) must be specified.  Note! - This tool can also be initiated directly from a python script using:
```python
  import pythonaddins
  pythonaddins.GPToolDialog(r'<path to toolbox>/LGsPythonToolbox.pyt', 'BreakupShapefile')
```

### 2. Shapefile to KMZ Tool: 
This tool accepts one or more shapefiles and converts each on to a corresponding KMZ file.  A desired output folder is required.  Note! - This tool can also be initiated directly from a python script using:
```python
  import pythonaddins
  pythonaddins.GPToolDialog(r'<path to toolbox>/LGsPythonToolbox.pyt', 'ShapefileToKMZ')
```

### 3. KMZ to Shapefile Tool: 
This tool accepts a KMZ file and converts it to a corresponding shapefile.  A desired output folder is required.  Note! - This tool can also be initiated directly from a python script using:
```python
  import pythonaddins
  pythonaddins.GPToolDialog(r'<path to toolbox>/LGsPythonToolbox.pyt', 'KMZToShapefile')
```
