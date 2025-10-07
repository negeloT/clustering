import arcpy
import numpy

import dbscan as dbs

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "DBSCANpoints"
        self.alias = ""

        # List of tool classes associated with this toolbox
        self.tools = [DBSCANpts]


class DBSCANpts(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "DBSCAN Points"
        self.description = "ArcGIS port of DBSCAN clustering algorithm"
        self.canRunInBackground = True

    def getParameterInfo(self):
        """Define parameter definitions"""

        fc = arcpy.Parameter(
            displayName="Input Point Features",
            name="fc",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        minpts = arcpy.Parameter(
            displayName="Minimum number of points",
            name="minpts",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        minpts.value = 3

        mindist = arcpy.Parameter(
            displayName="Cluster distance",
            name="mindist",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input")
        mindist.value = 1000


        fld = arcpy.Parameter(
            displayName="Cluster Field",
            name="fld",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        fld.value = 'Cluster'
        #
        # params = [fc, minpts, mindist, fld]

        params = [fc, fld, minpts, mindist]

        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        input = parameters[0].valueAsText
        fld = str(parameters[1].valueAsText)
        min_pts = int(parameters[2].valueAsText)
        min_dist = float(parameters[3].valueAsText)

        npts = int(arcpy.GetCount_management(input).getOutput(0))

        in_matrix = numpy.zeros((2, npts))
        i = 0

        for row in arcpy.da.SearchCursor(input, ["SHAPE@XY"]):
            x, y = row[0]
            in_matrix[0, i] = x
            in_matrix[1, i] = y
            i += 1

        clusters = dbs.dbscan_execute(in_matrix, min_dist, min_pts, arcpy.AddMessage)

        arcpy.AddMessage(len(clusters))
		#arcpy.AddMessage(fld)

        fieldnames = [field.name for field in arcpy.ListFields(input)]
        if not (fld in fieldnames):
            arcpy.AddField_management(input, fld, "LONG")

        i = 0
        rows = arcpy.da.UpdateCursor(input, fld)
        for row in rows:
            row[0] = clusters[i]
            rows.updateRow(row)
            i += 1

        return