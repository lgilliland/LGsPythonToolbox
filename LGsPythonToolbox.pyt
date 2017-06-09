import arcpy
import os
import linecache  # required for capture_exception()
import sys  # required for capture_exception()


# Common function used by many!!
def capture_exception():
    # Not clear on why "exc_type" has to be in this line - but it does...
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    filename = f.f_code.co_filename
    linecache.checkcache(filename)
    line = linecache.getline(filename, lineno, f.f_globals)
    s = '### ERROR ### [{}, LINE {} "{}"]: {}'.format(filename, lineno, line.strip(), exc_obj)
    return s


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def DoShapefileExtraction(shapef_to_process, where_clause, unique_field, shapef_out_dir):
    """ Description:
            Given a shapefile to process, query the file (using the optional where_clause) and extract each feature
            found into its own shapefile. The name of the individual feature shapefile will be based on the
            unique field passed in, and will be located in the specified shapefile output dir.
        Params:
            shapef_to_process:  Path to shapefile to process
            where_clause:       SQL Where clause to use when querying the source shapefile for features to process
            unique_field:       Field in the shapefile to use for uniquely naming the resulting shapefiles
            shapef_out_dir:     Folder where new shapefiles will exist
    """
    try:
        arcpy.AddMessage("Extracting from Shapefile: {0}".format(shapef_to_process))
        arcpy.AddMessage("      OutDir: {0}".format(shapef_out_dir))

        # Turn off adding result layers automatically to the map. This is so all of the generated
        # shapefiles don't get added to the map TOC.
        arcpy.env.addOutputsToMap = 0
        arcpy.env.overwriteOutput = True

        # Query the shapefile and get the rows to process... depending on the where_clause passed in
        if where_clause is None:
            rows = arcpy.da.SearchCursor(shapef_to_process, ["OID@", unique_field, "SHAPE@"])
        else:
            rows = arcpy.da.SearchCursor(shapef_to_process, ["OID@", unique_field, "SHAPE@"], where_clause)

        for row in rows:

            # Get the OID and unique_field values of the current row
            oid = row[0]
            unique_val = row[1]
            arcpy.AddMessage("Processing Item: {0}".format(unique_val))

            # Check to see if the unique_field passed represents a numeric field...
            if is_number(unique_val):
                # If the unique_field represents a number field, prepend the value with
                # "shape_" to make a valid shapefile name.
                final_output_name = "shape_" + str(unique_val)
            else:
                # If the unique_field represents a string field, make sure to remove an single
                # quotes, dashes, or spaces to ensure a valid shapefile name.
                name_noQuotes = unique_val.replace("'", "")
                name_noQuotesnoDashes = name_noQuotes.replace("-", "")
                final_output_name = name_noQuotesnoDashes.replace(" ", "")

            # Use the select_analysis function to query the shapefile for the feature id
            # and save it into its own shapefile...
            shapefile_for_extract = os.path.join(shapef_out_dir, final_output_name + '.shp')
            arcpy.Select_analysis(shapef_to_process, shapefile_for_extract, '"FID"=' + str(oid))

    except:
        err = capture_exception()
        arcpy.AddError(err)


def KMZToShape(kmz_to_process, shape_out_dir):
    """ Description:
            Given a KMZ file to process and a desired output dir, convert the KMZ to a layer and then convert
            the layer to a shapefile. The shapefile file will be named similarly to the input KMZ file name.
            Note - A byproduct of this function is that it leaves a temp .gdb and .lyr files in the output folder.
        Params:
            kmz_to_process:     Path to KMZ file to process
            shape_out_dir:      Folder where new shapefile will exist
    """
    try:
        # Allow overwriting...
        arcpy.env.overwriteOutput = True

        # Split up the file name and path...
        kmzPath, kmzFileLongName = os.path.split(kmz_to_process)
        kmzShortName = kmzFileLongName.rstrip(".kmz")

        # Process KML To Layer - Per the docs, output will be generated in the WGS84 coordinate system
        arcpy.AddMessage("    ...Processing KMZ file: {0}".format(kmz_to_process))
        arcpy.KMLToLayer_conversion(kmz_to_process, shape_out_dir, kmzShortName, "NO_GROUNDOVERLAY")
        # Note - Function only accepts the name of the file .gdb.  Apparently, it creates the feature dataset
        # named "Placemarks" within the .gdb. The feature class(es) is/are then created in the feature dataset and
        # named based on the type of features that are present. By default, polygon features get created
        # in the "...\<file.gdb>\Placemarks\Polygons" feature class.  Point features would be created
        # in the "...\<file.gdb>\Placemarks\Points" feature class.
        # So below, we are building the path and setting the env workspace based on these facts.

        # Build the path to the file GDB and feature dataset location and set as the active workspace...
        gdbPath = os.path.join(shape_out_dir, kmzShortName + ".gdb")
        gdbDataSetPath = os.path.join(gdbPath + "\\Placemarks")
        arcpy.env.workspace = gdbDataSetPath

        # Each data type will have its own feature class in the file gdb.
        featureclasses = arcpy.ListFeatureClasses()
        for fc in featureclasses:
            gdbFeatClassPath = os.path.join(gdbDataSetPath, fc)
            arcpy.AddMessage("        - Processing feature class: {0}".format(gdbFeatClassPath))

            # Was planning to use the FeatureClassToShapefile_conversion() function, but it does not allow you to
            # name the output shapefile. (It just takes the name of the input feature class, and in this case,
            # we can't control the name of the input feature class from the KMLToLayer_conversion() call above.)
            # arcpy.FeatureClassToShapefile_conversion(gdbFeatClassPath, shape_out_dir)
            # So instead, we will use this function...
            arcpy.FeatureClassToFeatureClass_conversion(fc, shape_out_dir, kmzShortName + "_" + fc)
            arcpy.AddMessage("        - Created new shapefile: {0}"
                             .format(shape_out_dir + "\\" + kmzShortName + "_" + fc + ".shp"))

        # Tried to cleanup the .gdb file and the .lyr file created by KMLToLayer_conversion(), but the
        # file gdb is currently locked...
        # arcpy.Delete_management(gdbPath)
        # arcpy.Delete_management(os.path.join(shape_out_dir, kmzShortName + ".lyr"))

    except:
        err = capture_exception()
        arcpy.AddError(err)


def ShapeToKMZ(shapef_to_process, kmz_out_dir):
    """ Description:
            Given a shapefile to process and a desired output dir, generate an 'in memory' layer from the
            shapefile and then export the layer as a .kmz file. The .kmz file will be named similarly to the
            input shapefile name.
        Params:
            shapef_to_process:  Path to shapefile to process
            kmz_out_dir:        Folder where new KMZ files will exist
    """
    try:
        arcpy.AddMessage("Processing Shapefile to KMZ: {0}".format(shapef_to_process))
        # arcpy.AddMessage("        OutDir: {0}".format(kmz_out_dir))

        # Get the path where the mxd file is located...
        shapePath, shapeFileLongName = os.path.split(shapef_to_process)
        if os.path.exists(shapePath):
            arcpy.env.workspace = shapePath

        shapeShortName = shapeFileLongName.rstrip(".shp")
        # Build the name of the KMZ file
        kmz_file = shapeShortName + ".kmz"
        # Build the full path to the KMZ file
        kmz_path_file = os.path.join(kmz_out_dir, kmz_file)

        # Turn off adding result layers automatically to the map, and allow overwriting.
        arcpy.env.addOutputsToMap = 0
        arcpy.env.overwriteOutput = True

        # Use the name of the shapefile to make a 'temporary' layer (per esri, the layer is temporary and
        # will be released when it goes out of scope if it is not saved.)
        arcpy.MakeFeatureLayer_management(shapeFileLongName, shapeShortName)

        # Now use the layer in the Layer-to-KML tool.  The output is a zipped KML (or KMZ)
        arcpy.LayerToKML_conversion(shapeShortName, kmz_path_file)

    except:
        err = capture_exception()
        arcpy.AddError(err)


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the .pyt file)."""
        self.label = "LGsPythonToolbox"
        self.alias = "lgtools"

        # List of tool classes (as defined below) associated with this toolbox
        self.tools = [BreakupShapefile, ShapefileToKMZ, KMZToShapefile]


class BreakupShapefile(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Breakup Shapefile Tool"
        self.description = "Reads a shapefile and breaks it up into individual shapefiles for each feature found."
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        Features = arcpy.Parameter(
            displayName="Input Features",
            name="in_features",
            datatype="GPFeatureRecordSetLayer",
            # datatype="DETable",
            parameterType="Required",
            direction="Input")

        SQL = arcpy.Parameter(
            displayName="SQL Where Clause",
            name="in_sql",
            datatype="SQL Expression",
            parameterType="Optional",
            direction="Input")

        SQL.parameterDependencies = [Features.name]

        Fields = arcpy.Parameter(
            displayName="Unique Name Field",
            name="in_field",
            datatype="GPString",
            parameterType="Required",
            direction="Input")

        Fields.filter.type = "ValueList"
        Fields.filter.list = []

        Folder = arcpy.Parameter(
            displayName="Output Folder",
            name="out_folder",
            datatype="DEFolder",
            parameterType="Required",
            direction="Input")

        # parameter list
        params = [Features, SQL, Fields, Folder]

        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        if parameters[0].altered:
            desc = arcpy.Describe(parameters[0])
            fields = desc.fields
            list = []
            for f in fields:
                # We should only allow strings and numbers as valid fields to use for a unique name.
                if f.type == 'String' or f.type == 'Integer' or f.type == 'OID' \
                        or f.type == 'Double' or f.type == 'Single' or f.type == 'SmallInteger':
                    list.append(f.name)  # Transfer name to new list
            parameters[2].filter.list = list

        # Check to see if param 1 has changed, and if so, clear the SQL clause...
        ## CAN'T SEEM TO GET THIS WORKING! The code below exhibits the desired behavior when working in the GUI,
        ## But, when you click OK, parameters[1].valueAsText = None and parameters[1].value = None
        # if (not parameters[0].hasBeenValidated) and (parameters[0].altered):
        #     parameters[1].value = ''

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        try:
            shapef = parameters[0].valueAsText
            sql = parameters[1].valueAsText
            unique_namer = parameters[2].valueAsText
            outDir = parameters[3].valueAsText

            # Describe the input from the user...
            desc = arcpy.Describe(shapef)
            # Get the source file name from the layer...
            fullShapefile = desc.catalogPath

            # Call the function to process through the shapefile...
            arcpy.AddMessage("SQL is {0}".format(sql))
            DoShapefileExtraction(fullShapefile, sql, unique_namer, outDir)
            arcpy.AddWarning("Done!")

        except:
            err = capture_exception()
            arcpy.AddError(err)


class ShapefileToKMZ(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Shapefile to KMZ Tool"
        self.description = "Processes one or more shapefiles and creates a corresponding KMZ file."
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        Features = arcpy.Parameter(
            displayName="Shapefile to Process",
            name="in_shapefiles",
            # datatype="Feature Set",
            # datatype="DEDatasetType",
            datatype="DEFile",
            parameterType="Required",
            direction="Input",
            multiValue="True")

        Features.filter.list = ['shp']

        Folder = arcpy.Parameter(
            displayName="Output Folder",
            name="out_folder",
            datatype="DEFolder",
            parameterType="Required",
            direction="Input")

        # parameter list
        params = [Features, Folder]

        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal validation is
        performed.  This method is called whenever a parameter has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """Get the value entered and create a new shapefile using the value as the basis for the name."""
        try:
            # Grab the multivalue parameter value and parse it into a list
            myDatasets = parameters[0].valueAsText
            myDatasetList = myDatasets.split(";")

            # Grab the specified output dir
            outDir = parameters[1].valueAsText

            # Process each dataset
            for mDataset in myDatasetList:
                # mDataset contains an individual dataset string (ex: 'E:\Code\_PythonToolbox\ReadMe.txt')
                # BEWARE - The mDataset string also contains the single quotes. Maybe this is an artifact of being read
                # from the multivalue toolbox tool parameter???  Anyway, be sure to remove any single quotes...
                mDataset_noQuotes = mDataset.replace("'", "")
                ShapeToKMZ(mDataset_noQuotes, outDir)

            arcpy.AddWarning("Done!")

        except:
            err = capture_exception()
            arcpy.AddError(err)


class KMZToShapefile(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "KMZ to Shapefile Tool"
        self.description = "Processes KMZ file into a corresponding shapefile."
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        Features = arcpy.Parameter(
            displayName="KMZ File to Process",
            name="in_kmz",
            datatype="DEFile",
            parameterType="Required",
            direction="Input",
            multiValue="False")

        Features.filter.list = ['kmz']

        Folder = arcpy.Parameter(
            displayName="Output Folder",
            name="out_folder",
            datatype="DEFolder",
            parameterType="Required",
            direction="Input")

        # parameter list
        params = [Features, Folder]

        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal validation is
        performed.  This method is called whenever a parameter has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """Get the value entered and create a new shapefile using the value as the basis for the name."""
        try:
            # Grab the parameter values
            myKMZ = parameters[0].valueAsText
            outDir = parameters[1].valueAsText

            # Call function to process...
            KMZToShape(myKMZ, outDir)
            arcpy.AddWarning("Done!")

        except:
            err = capture_exception()
            arcpy.AddError(err)
