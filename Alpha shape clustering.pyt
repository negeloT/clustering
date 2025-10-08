# coding=utf-8
import arcpy

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = ""

        # List of tool classes associated with this toolbox
        self.tools = [ClusteringSettlementSystem, ClusteringQualityCriterion]


class ClusteringSettlementSystem(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Clustering the settlement system"
        self.description = "Algorithm for selecting regions and centroids of clusters"
        self.canRunInBackground = True

    def getParameterInfo(self):
        """Define parameter definitions"""
        input_points = arcpy.Parameter(  # Входной слой точек
            displayName="Input points",
            name="input_points",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        cluster_field = arcpy.Parameter(  # Название поля, в котором хранятся марки кластеров
            displayName="Cluster ID Field",
            name="in_field",
            datatype="Field",
            parameterType="Required",
            direction="Input")

        cluster_field.parameterDependencies = [
            input_points.name]  # Тут мы связываем поле с входным слоем (чтобы поле выбиралось из выбранного слоя)

        cluster_distance = arcpy.Parameter(  # Расстояние кластеризации
            displayName="Cluster distance",
            name="cluster_distance",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")

        output_polygons = arcpy.Parameter(  # Выходной слой альфа-оболочек
            displayName="Output regions feature class",
            name="output_polygons",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output")

        output_points = arcpy.Parameter(  # Выходной слой центроидов
            displayName="Output centroids feature class",
            name="output_points",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output")

        params = [input_points, cluster_field, cluster_distance, output_polygons,output_points]
        # Здесь мы в список передаем все вводимые параметры
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
        input_points = parameters[0].valueAsText
        cluster_field = parameters[1].valueAsText
        cluster_distance = int(parameters[2].valueAsText)
        output_polygons = parameters[3].valueAsText
        output_points = parameters[4].valueAsText

        # 1. Создаём пустой полигональный класс пространственных объектов для выходных полигонов
        path = output_polygons[:output_polygons.rfind('\\') + 1]  # Вырезаем путь к папке
        name = output_polygons[output_polygons.rfind('\\') + 1:]  # Вырезаем название файла
        spatial_reference = arcpy.Describe(input_points).spatialReference
        # Тут мы вытаскиваем систему координат входных точек
        arcpy.CreateFeatureclass_management(path, name, "POLYGON", '', 'DISABLED', 'DISABLED', spatial_reference)
        arcpy.AddField_management(output_polygons, "PNT_COUNT", 'SHORT')  # добавляем поле PNT_Count, чтобы потом можно было
        # Присоединить полигоны (см. шаг 10)

        # 2. Извлекаем все значения поля, хранящего идентификаторы кластеров в список
        with arcpy.da.SearchCursor(input_points, cluster_field) as cursor:
            cluster_list = [row[0] for row in cursor]

        # 3. Преобразуем полученный список в множество (set(...)), чтобы оставить в нем только уникальные значения.
        cluster_set = set(cluster_list)

        # 4. Создаём слой для входного класса объектов точек (MakeFeatureLayer_management(...)).
        arcpy.MakeFeatureLayer_management(input_points, "input_points_lyr")

        # 5. Организуем цикл по элементам полученного на шаге 3 множества.
        for cluster_num in cluster_set:
            # 6. Выбираем точки, номер кластера которых совпадает с переменной цикла — текущим номером кластера
            where_clause = '"{0}" = {1}'.format(cluster_field, cluster_num)
            arcpy.SelectLayerByAttribute_management("input_points_lyr", "NEW_SELECTION", where_clause)

            # 7. Для выбранных точек запускаем процедуру регионизации (AggregatePoints_cartography). В качестве
            # расстояния кластеризации необходимо указывать удвоенное расстояние, использованное ранее в методе
            # DBSCAN. В этом случае оболочки будут соответствовать исходным кластерам.
            output_regions = "in_memory/output_regions"
            arcpy.AggregatePoints_cartography("input_points_lyr", output_regions, cluster_distance)

            # 8. Для полученных регионов кластеров необходимо выполнить операцию объединения (Dissolve), так как они
            # могут состоять из нескольких оболочек, касающихся в одной точке.
            output_polygons_lyr = "in_memory/output_polygons_lyr"
            arcpy.Dissolve_management(output_regions, output_polygons_lyr, None, None, "SINGLE_PART")

            # 9. Рассчитайте количество точек в текущем кластере и запишите его в поле Count текущего полигона.
            out_tab = 'in_memory/output_table'
            # инструмент статистики для подсчёта количества точек
            arcpy.TabulateIntersection_analysis(output_polygons_lyr, 'FID', input_points, out_tab , '', '', '', '')
            # присоединение поля
            arcpy.JoinField_management(output_polygons_lyr, 'FID', out_tab, 'FID', 'PNT_COUNT')

            # 10. Добавляем текущий полигон в выходной полигональный класс (1).
            arcpy.Append_management(output_polygons_lyr, output_polygons, "NO_TEST")

        # 11. После выполнения цикла конвертируем полигоны в выходные точки центроидов (FeatureToPoint_management).
        arcpy.FeatureToPoint_management(output_polygons, output_points, "INSIDE")

        return

class ClusteringQualityCriterion(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Clustering quality criterion"
        self.description = "Calculation of the clustering quality criterion"
        self.canRunInBackground = True

    def getParameterInfo(self):
        """Define parameter definitions"""
        input_points = arcpy.Parameter(  # Входной слой точек
            displayName="Input points",
            name="input_points",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        cluster_field = arcpy.Parameter(  # Название поля, в котором хранятся марки кластеров
            displayName="Cluster ID Field",
            name="in_field",
            datatype="Field",
            parameterType="Required",
            direction="Input")

        cluster_field.parameterDependencies = [
            input_points.name]  # Тут мы связываем поле с входным слоем (чтобы поле выбиралось из выбранного слоя)

        params = [input_points, cluster_field]
        # Здесь мы в список передаем все вводимые параметры
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
        input_points = parameters[0].valueAsText
        cluster_field = parameters[1].valueAsText
        # Создаём пустой словарь для хранения координат кластера
        clusters = {}
        # Создаём курсор поиска для чтения данных
        with arcpy.da.SearchCursor(input_points, ["SHAPE@X", "SHAPE@Y", cluster_field]) as cursor:
            for row in cursor:
                # Получаем координаты x и y и номер кластера
                x = float(row[0])
                y = float(row[1])
                cluster = row[2]
                # Добавляем координаты в соответствующий кластер
                if cluster in clusters:
                    clusters[cluster].append((x, y))
                else:
                    clusters[cluster] = [(x, y)]

        # Рассчитываем внутри-кластерное расстояние
        intra_cluster_sum = 0
        intra_counter = 0
        #Проходим циклом по ключам словря
        for key in clusters:
            #По ключу вытаскиваем список координт
            cluster = clusters[key]
            #Пробегаемся по всей длине списка координат (берем одну координату)
            for i in range(len(cluster)):
                #Пробегаем по все оставшимся координатам)
                for j in range(i+1, len(cluster)):
                    intra_cluster_sum += ((cluster[i][0] - cluster[j][0])**2 + (cluster[i][1] - cluster[j][1])**2)**0.5
                    intra_counter += 1

        intra_result = intra_cluster_sum / intra_counter

        # Выводим результат
        arcpy.AddMessage("Average intracluster distance {}".format(intra_result))

        # Рассчитываем меж-кластерное расстояние
        inter_cluster_sum = 0
        inter_counter = 0
        #Получаем список ключей из словаря
        dict_keys = [i for i in clusters]
        #Пробегаем по длине списка ключей из словаря
        for i in range(len(dict_keys)): #0 1 2 3 ...
            #Получаем список координат по ключу
            cluster = clusters[dict_keys[i]]
            #Пробегаемся по списку координат (берем одну)
            for j in range(len(cluster)):
                #Берем следующий кластер, после нашего i+1 - это значит следующий ключ в списке ключей dict_keys
                for k in range(i+1, len(dict_keys)):
                    #Получаем по этому ключу список координат кластера
                    cluster_k = clusters[dict_keys[k]]
                    #Пробегаемся по этому списку координат
                    for l in range(len(cluster_k)):
                        inter_cluster_sum += ((cluster[j][0] - cluster_k[l][0]) ** 2 + (cluster[j][1] - cluster_k[l][1]) ** 2) ** 0.5
                        inter_counter += 1

        inter_result = inter_cluster_sum / inter_counter

        # Выводим результат
        arcpy.AddMessage("Average inter-cluster distance {}".format(inter_result))
        
        # Выводим соотношение
        arcpy.AddMessage("Ratio {}".format(intra_result / inter_result))

        return

