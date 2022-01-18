import os
import json
import simplekml
import numpy as np
from shapely.geometry import shape, Polygon
from ipyleaflet import Map, ScaleControl, GeoJSON, DrawControl, WidgetControl,  Popup, FullScreenControl
from IPython.display import display
from ipywidgets import Layout
from ipywidgets.widgets import HTML, RadioButtons, ToggleButton, ToggleButtons, BoundedIntText, Button, HBox, VBox, \
    Output, Checkbox, \
    Label, Dropdown, Textarea
from shapely.geometry import Point as shPoint
from IPython.display import Javascript
import pandas as pd
from explorer_utils import *


class MapExplorer:

    def __init__(self, area_geojson_feature, cams_path, pred_path, output_path, zoom=14, impianti_in_area=None, show_pred_score=False):
        self.comune = area_geojson_feature
        self.zoom = zoom

        self.cams_path = cams_path
        self.pred_path = pred_path
        self.output_path = output_path
        self.impianti_in_area = impianti_in_area
        self.points = self.__obtain_list(self.comune)
        self.__set_outbounds()
        self.out = Output()
        self.show_pred_score = show_pred_score
        self.__prepare_map(self.comune, self.outside, self.points, self.zoom, self.cams_path, self.pred_path,
                           self.output_path, self.impianti_in_area)
        self.waste_type = [ "Non identifiable", "VEHICLES", "TYRES", "SLUDGE, MANURE", "Rubble/excavated earth and rocks", "WOOD",  "Scrap", "Domistic appliances", "Plastic", "Paper",  "Glass",
"Corrugated sheets(asbestos-cement)", "Bulby waste", "Foundry waste","Stone /marble processing waste", "Asphalt milling", "Other"]
        self.storage_mode = ["Delimited heaps","Heaps not delimited","Filled pallets", "Filled roll-off containers", "Cages", "Big bags","Silos", "Plastic tanks","Drums, barrels", "Other"]
    def __set_outbounds(self):
        polygon = shape(self.comune["geometry"])
        lonmin, latmin, lonmax, latmax = polygon.bounds
        offsetx = offsety = 0.005
        outside = Polygon([[lonmin - offsetx, latmin - offsety], [lonmax + offsetx, latmin - offsety],
                           [lonmax + offsetx, latmax + offsety], [lonmin - offsetx, latmax + offsety],
                           [lonmin - offsetx, latmin - offsety]])
        self.outside = outside.symmetric_difference(polygon).difference(polygon).__geo_interface__

    def show_map(self):
        self.m.layout.width = '100%'
        self.m.layout.height = "500px"  # '300px'
        self.m.fullscreen = True
        self.__clear_output()
        box = VBox([ self.out, self.m])
        display(box)

    def __create_map(self, lat, lon, zoom):
        m = Map(center=(lat, lon), zoom=zoom, min_zoom=10, max_zoom=22)
        m.add_control(ScaleControl(position='bottomleft'))
        m.clear_layers()
        return m

    def __prepare_map(self, comune_feature, outside, points, zoom, cams_path, pred_path, output_path, impianti_in_area):
        s = shape(comune_feature["geometry"])
        lon, lat = s.centroid.x, s.centroid.y
        self.m = self.__create_map(lat, lon, zoom)
        self.m.add_control(FullScreenControl())
        self.__add_right_click(self.m, output_path)
        print("Base map created")

        # layers

        google_layer = get_google_layer()
        self.m.add_layer(google_layer)
        orthophoto_layer15 = get_ortophoto_layer15()
        self.m.add_layer(orthophoto_layer15)
        orthophoto_layer = get_ortophoto_layer()
        self.m.add_layer(orthophoto_layer)
        self.__add_toggle_map_shown(self.m, google_layer, orthophoto_layer, orthophoto_layer15)
        print("Images layers providers added")

        self.m.add_layer(GeoJSON(data=comune_feature, style={'fill': 0, 'stroke-width': 4}))
        self.m.add_layer(GeoJSON(data=outside, style={'fillOpacity': 0.4}, hover_style={'fillOpacity': 0}))
        print("Limits drawn")
        
        
        # controlls
        self.lc = get_color_legend()
        self.m.add_control(self.lc)
        self.__add_draw_control(self.m)
        self.__add_scroll_index(self.m, self.points)
        self.__add_download_btn(self.m, output_path)
        self.__add_download_btn_excel(self.m, output_path)
        btn_impianti = self.__add_impianti_in_area(self.m, impianti_in_area)
        print("Draw controls added")

        # Load cams and predictions
        self.result_btn = self.__add_model_result_layers(self.m, cams_path, pred_path)

        self.suspicius_sites, self.counter = self.__add_previous_annotations(self.m, output_path)
        print("Previous annotations loaded")

    def __add_impianti_in_area(self, m, path):
        if path is None:
            return
        impianti_GeoJSON_obj = add_impianti_layer(m, path)
        btn_impianti = Checkbox(value=True,description='ITRIF',disabled=False,indent=False)
        
        def show_impianti(e):
            if e["new"]:
                m.add_layer(impianti_GeoJSON_obj)
            else:
                m.remove_layer(impianti_GeoJSON_obj)
                
        btn_impianti.observe(show_impianti, names='value')
        toggle_control = WidgetControl(widget=btn_impianti, position='topleft', max_width=70)
        m.add_control(toggle_control)
        return btn_impianti
            
    def __add_model_result_layers(self, m, cams_path, pred_path):
        if cams_path is None and pred_path is None:
            return None
        options = []
        if not cams_path is None and not pred_path is None:
            options.append("Both")
            
        if not cams_path is None:
            options.append("None")
            options.append("CAMs")
            print("Loading CAMs layer...")
            cams_GeoJSON_obj = add_cams_layer(m, cams_path)
            print("Cams layer added")
            
        if not pred_path is None:
            options.append("Preds")
            print("Loading Predictions layer...")
            preds_GeoJSON_obj = add_prediction_layer(m, pred_path, self.show_pred_score)
            print("Predictions layer added")

        btn = RadioButtons(
            options=options,
            disabled=False,
            value = "Both",
            layout=dict(width='70px')
        )

        def toggle_layers(btn):

            if btn["new"] == "Both":
                if not cams_GeoJSON_obj in m.layers:
                    m.add_layer(cams_GeoJSON_obj)
                if not preds_GeoJSON_obj in m.layers:
                    m.add_layer(preds_GeoJSON_obj)
            elif btn["new"] == "CAMs":
                if not cams_GeoJSON_obj in m.layers:
                    m.add_layer(cams_GeoJSON_obj)
                if preds_GeoJSON_obj in m.layers:
                    m.remove_layer(preds_GeoJSON_obj)
            elif btn["new"] == "Preds":
                if not preds_GeoJSON_obj in m.layers:
                    m.add_layer(preds_GeoJSON_obj)
                if cams_GeoJSON_obj in m.layers:
                    m.remove_layer(cams_GeoJSON_obj)
            else:
                if preds_GeoJSON_obj in m.layers:
                    m.remove_layer(preds_GeoJSON_obj)
                if cams_GeoJSON_obj in m.layers:
                    m.remove_layer(cams_GeoJSON_obj)

        btn.observe(toggle_layers, names='value')

        toggle_control = WidgetControl(widget=btn, position='bottomleft', max_width=70)
        m.add_control(toggle_control)
        return btn

    def __add_toggle_map_shown(self, m, google_layer, orthophoto_layer, orthophoto15_layer):
        radio_map_choice = RadioButtons(
            options=['Orthophoto18', 'Orthophoto15', 'Gmaps'],
            value='Orthophoto18', 
            layout=Layout(width='120px'))

        def change_shown_map(value):
            if value['new'] == 'Gmaps':
                google_layer.visible = True
                orthophoto_layer.visible = False
                orthophoto15_layer.visible = False
            elif value['new'] == 'Orthophoto18':
                google_layer.visible = False
                orthophoto_layer.visible = True
                orthophoto15_layer.visible = False
            else:
                google_layer.visible = False
                orthophoto_layer.visible = False
                orthophoto15_layer.visible = True

        radio_map_choice.observe(change_shown_map, names='value')

        toggle_map_control = WidgetControl(widget=radio_map_choice, position='bottomleft', max_width=120)
        m.add_control(toggle_map_control)

    ################### HANDLE POLYGONS LAYER ###########
    def __get_layer_with_feature_id(self, current_id):
        for l in self.m.layers:
            if type(l) == type(GeoJSON()) and "id" in l.data and l.data["id"] == current_id:
                return l

    def __create_feature_geojson(self, feature, current_id):

        feature["id"] = current_id
        return GeoJSON(
            data=feature,
            style={
                'opacity': 1, 'dashArray': '2', 'fillOpacity': 0.1, 'weight': 2, 'color': '#fafafa'
            },
            hover_style={
                'color': 'green', 'dashArray': '0', 'fillOpacity': 0.1
            }
            # style_callback=random_color
        )

    def __on_draw_handler(self, dc, action, geo_json):

        if action == "created" and geo_json["geometry"]["type"] == "Polygon":
            dc.clear()
            self.counter += 1
            geo_json_layer = self.__create_feature_geojson(geo_json, self.counter)
            geo_json_layer.on_click(self.__click_handler)
            self.m.add_layer(geo_json_layer)
            self.__click_handler(event='click', feature=geo_json_layer.data)
            self.suspicius_sites[geo_json_layer.data["id"]] = geo_json_layer.data
            self.__dump_annotations()

    def __add_draw_control(self, m):
        draw_control = DrawControl(circlemarker={}, polyline={})
        draw_control.edit = False
        draw_control.remove = False
        draw_control.on_draw(self.__on_draw_handler)
        m.add_control(draw_control)

    def __add_right_click(self, m, output_path):
        message = HTML()
        popup = Popup(child=message, close_button=True, auto_close=True, close_on_escape_key=True, keep_in_view=True)
        path = output_path.replace(".json", "_point.kml")

        def handle_interation(**kwargs):
            if kwargs.get('type') == 'contextmenu':
                if popup in m.layers:
                    m.remove_layer(popup)
                lat, lon = kwargs.get('coordinates')
                popup.location = lat, lon
                message.value = '{:.7f}, {:.7f}<br><a href="/files{}" target="_blank"> Download as KML</a> '.format(lat, lon, path)
                kml = simplekml.Kml()
                nt = kml.newpoint(description="Coordinates: {},{}".format(lat, lon), coords=[(lon, lat)])  # lon, lat optional height
                kml.save(path)
                popup.child = message
                m.add_layer(popup)

        m.on_interaction(handle_interation)

 
    ################# CAMS ##################

    def __click_handler(self, event=None, id=None, properties=None, feature=None):
        current_id = feature["id"]
        feature["properties"]["fill-opacity"] = 1
        l = self.__get_layer_with_feature_id(current_id)

        with self.out:
            self.out.clear_output()
            display(self.__get_widgets(l))

        self.m.fullscreen = False
        
    def __create_kml(self, path):
    
        kml_new = simplekml.Kml()
        for key in self.suspicius_sites:
            site = self.suspicius_sites[key]
            tuples = []
            for c in site['geometry']["coordinates"][0]:
                tuples.append((c[0], c[1]))
                
            des = "<p>Severity:{}<p>".format(
                site["properties"]["Severity"] if "Severity" in site["properties"] and len(site["properties"]["Severity"]) > 0 else "Not defined")

            des += "<p>Certainty:{}<p>".format(
                site["properties"]["Certainty"] if "Certainty" in site["properties"] and len(site["properties"]["Certainty"]) > 0 else "Not defined")
            
            des += "<p>Environmental Risk:{}<p>".format(
                site["properties"]["EnvironmentalRisk"] if "EnvironmentalRisk" in site["properties"] and len(site["properties"]["EnvironmentalRisk"]) > 0 else "Not defined")

            des += "<p>WasteTypes:{}<p>".format(
                site["properties"]["WasteTypes"] if "WasteTypes" in site["properties"] else "[]")
            
            des += "<p>Description:{}<p>".format(
                site["properties"]["Description"] if "Description" in site["properties"] and len(site["properties"]["Description"]) > 0 else "")

            pol = kml_new.newpolygon(name="{}".format(key), description=des, outerboundaryis=tuples)

        kml_new.save(path)

    def __create_excel(self, path):
        results_excel = []
        for k in self.suspicius_sites:
            site = self.suspicius_sites[k]
            geometry = shape(site["geometry"])
            results_excel.append([site["properties"]["Severity"] if "Severity" in site["properties"] else None,
                                  site["properties"]["Certainty"] if "Certainty" in site["properties"] else None,
                                  site["properties"]["EnvironmentalRisk"] if "EnvironmentalRisk" in site["properties"] else None,
                                  site["properties"]["WasteTypes"] if "WasteTypes" in site["properties"] else None,
                                  site["properties"]["Description"] if "Description" in site["properties"] else None,
                                  "{}, {}".format(geometry.centroid.x, geometry.centroid.y)])

        df = pd.DataFrame.from_records(results_excel, columns=["Severity", "Certainty","EnvironmentalRisk", "WasteTypes", "Description", "Coordinates"])
        df.to_excel(path, sheet_name='sites')

    def __add_download_btn_excel(self, m, output_path):
        path = output_path.replace(".json", ".xlsx")

        def on_download_btn_excel_clicked(event):
            self.__create_excel(path)
            url = "/files" + path
            display(Javascript('window.open("{url}");'.format(url=url)))

        download_btn_excel = Button(disabled=False, button_style='', icon='table',
                                    layout=Layout(width='35px', height='30px'))
        download_btn_excel.on_click(on_download_btn_excel_clicked)
        toggle_cams_control = WidgetControl(widget=download_btn_excel, position='topright')
        m.add_control(toggle_cams_control)

    def __add_download_btn(self, m, output_path):
        path = output_path.replace(".json", ".kml")

        def on_download_btn_clicked(event):
            self.__create_kml(path)
            url = "/files" + path
            display(Javascript('window.open("{url}");'.format(url=url)))

        download_btn = Button(disabled=False, button_style='', icon='download',
                              layout=Layout(width='35px', height='30px'))
        download_btn.on_click(on_download_btn_clicked)
        toggle_cams_control = WidgetControl(widget=download_btn, position='topright')
        m.add_control(toggle_cams_control)

    ############## ANNOTATE POLYGONGS #############
    def __add_previous_annotations(self, m, output_path):
        suspicius_sites = dict()
        counter = 0

        if os.path.exists(output_path):
            with open(output_path, "r") as json_file:
                suspicius_sites = json.load(json_file)
            for key in suspicius_sites:
                geo_json_layer = self.__create_feature_geojson(suspicius_sites[key], key)
                geo_json_layer.on_click(self.__click_handler)
                m.add_layer(geo_json_layer)

                counter = max(counter, int(key))

        return suspicius_sites, counter

    def __get_severity_of_non_comliance_index(self, pvalue='Not specified'):

        return [Label(value='1 - Severity of suspected non compliance index:'), Dropdown(
            options=['Not specified', 'None', 'Low', 'Medium', 'High'],
            value=pvalue,
            description='')]
    
    
    def __get_non_comliance_index(self, pvalue='Not specified'):
        return [Label(value='2 - Non compliance certainty index:'), Dropdown(
            options=['Not specified', 'None', 'Low', 'Medium', 'High'],
            value=pvalue,
            description='')]
    
    def __get_environmental_risk(self, pvalue='Not specified'):
        return [Label(value='3 - Environmental Risk index:'), Dropdown(
            options=['Not specified', 'None', 'Low', 'Medium', 'High'],
            value=pvalue,
            description='')]
    
    def __get_description_widget(self, pvalue=""):
        return [Textarea(
            value=pvalue,
            placeholder='Type something',
            description='4 - Description:',
            disabled=False, 
            layout=Layout(flex='0 1 auto',height='auto', width='600px'))]

    def __get_values(self, llcb):
        values = []
        counter = 0
        for l in llcb:
            print(l)
            for cb in l:
                if cb.value:
                    values.append(self.waste_type[counter])
                counter += 1
        return values
    
    def __get_values_storage(self, llcb):
        values = []
        counter = 0
        for l in llcb:
            print(l)
            for cb in l:
                if cb.value:
                    values.append(self.storage_mode[counter])
                counter += 1
        return values

    def __get_waste_type_widget(self, values=[]):
        under = " "
        widgets_wt = []
        for wt in self.waste_type:
            widgets_wt.append(
                Checkbox(value=wt in values, description=f'{wt:{under}{"<"}{40}}', disabled=False, indent=False))
        ll = [Label(value='6 - Choose the waste types present:')]
        for i in range(0, len(self.waste_type), 3):
            ll.append(widgets_wt[i:i + 3])
        return ll
    
    def __get_storage_mode_widget(self, values=[]):
        under = " "
        widgets_wt = []
        for wt in self.storage_mode:
            widgets_wt.append(
                Checkbox(value=wt in values, description=f'{wt:{under}{"<"}{40}}', disabled=False, indent=False))
        ll = [Label(value='5 - Choose the storage mode:')]
        for i in range(0, len(self.storage_mode), 3):
            ll.append(widgets_wt[i:i + 3])
        return ll
    
    def __dump_annotations(self):
        with open(self.output_path, "w") as jsonFile:
            json.dump(self.suspicius_sites, jsonFile, indent=4)

    def __get_delete_button(self, feature_id):
        def on_delete_button_clicked(event):
            geojson_layer = self.__get_layer_with_feature_id(feature_id)
            # mapw.layers.index(geojson_layer)
            ll = list(self.m.layers)
            ll.remove(geojson_layer)
            del self.suspicius_sites[feature_id]
            self.__dump_annotations()
            self.m.layers = ll
            self.__clear_output()

        btn = Button(description='Delete polygon', disabled=False, button_style='danger', icon='trash')
        btn.on_click(on_delete_button_clicked)
        return btn

    def __get_save_button(self, feature_id):

        def on_save_btn_click(event):
            geojson_layer = self.__get_layer_with_feature_id(feature_id)
            self.m.layers.index(geojson_layer)
            ll = list(self.m.layers)
            ll.remove(geojson_layer)
            geojson_layer.data["properties"]["Severity"] = self.data_info["severityw"][1].value
            geojson_layer.data["properties"]["Certainty"] = self.data_info["certaintyw"][1].value
            geojson_layer.data["properties"]["EnvironmentalRisk"] = self.data_info["environmentalriskw"][1].value
            geojson_layer.data["properties"]["WasteTypes"] = self.__get_values(self.data_info["waste_typew"][1:])
            geojson_layer.data["properties"]["StorageMode"] = self.__get_values_storage(self.data_info["storage_modew"][1:])
            geojson_layer.data["properties"]["Description"] = self.data_info["descriptionw"][0].value

            ll.append(geojson_layer)

            self.suspicius_sites[feature_id] = geojson_layer.data
            self.__dump_annotations()

            self.__clear_output()

        btn = Button(description='Save information', disabled=False, button_style='info', icon='save')
        btn.on_click(on_save_btn_click)
        return btn

    def __clear_output(self):
        with self.out:
            self.out.clear_output()

    def __get_close_button(self):

        def on_close_btn_click(event):
            self.__clear_output()

        btn = Button(description='X', disabled=False, button_style='warning', icon='icon',
                     layout=Layout(width='40px', height='30px'))
        btn.on_click(on_close_btn_click)
        return btn

    def __get_widgets(self, geojson_layer):
        v1 = geojson_layer.data["properties"]['Severity'] if 'Severity' in geojson_layer.data[
            "properties"].keys() else 'Not specified'
        v2 = geojson_layer.data["properties"]['Certainty'] if 'Certainty' in geojson_layer.data[
            "properties"].keys() else 'Not specified'
        v3 = geojson_layer.data["properties"]['EnvironmentalRisk'] if 'EnvironmentalRisk' in geojson_layer.data[
            "properties"].keys() else 'Not specified'
        v4 = geojson_layer.data["properties"]['Description'] if 'Description' in geojson_layer.data[
            "properties"].keys() else ""
        v5 = geojson_layer.data["properties"]['StorageMode'] if 'StorageMode' in geojson_layer.data[
            "properties"].keys() else []
        v6 = geojson_layer.data["properties"]['WasteTypes'] if 'WasteTypes' in geojson_layer.data[
            "properties"].keys() else []

        self.data_info = {"delete": self.__get_delete_button(geojson_layer.data["id"]),
                          "save": self.__get_save_button(geojson_layer.data["id"]),
                          "close": self.__get_close_button(),
                          "severityw": self.__get_severity_of_non_comliance_index(v1),
                          "certaintyw": self.__get_non_comliance_index(v2),
                          "environmentalriskw": self.__get_environmental_risk(v3),
                          "descriptionw": self.__get_description_widget(v4),
                          "storage_modew": self.__get_storage_mode_widget(v5),
                          "waste_typew": self.__get_waste_type_widget(v6)}

        return VBox([HBox([self.data_info["delete"], self.data_info["save"], self.data_info["close"]]),
                     VBox([HBox(self.data_info["severityw"]),
                           HBox(self.data_info["certaintyw"]),
                           HBox(self.data_info["environmentalriskw"]),
                           HBox(self.data_info["descriptionw"]),
                           VBox([self.data_info["storage_modew"][0]] + [HBox(x) for x in
                                                                      self.data_info["storage_modew"][1:]]),
                           VBox([self.data_info["waste_typew"][0]] + [HBox(x) for x in
                                                                      self.data_info["waste_typew"][1:]])
                           ])
                     ])

    ################## ITERATION ##############
    def __obtain_list(self, area):
        offsetx = 0.004
        offsety = 0.002
        if area["geometry"]["type"] == "MultiPolygon":
            lons = [x[0] for x in area["geometry"]["coordinates"][0][0]]
            lats = [x[1] for x in area["geometry"]["coordinates"][0][0]]
        else:
            lons = [x[0] for x in area["geometry"]["coordinates"][0]]
            lats = [x[1] for x in area["geometry"]["coordinates"][0]]
        polygon_area = shape(area['geometry'])

        xmin, xmax = min(lons), max(lons)  # CHECK IF WE GO TO NEGATIVE LONGIGUTE
        ymin, ymax = min(lats), max(lats)  # CHECK IF WE GO TO NEGATIVE LATITUDE

        xx, yy = np.meshgrid(np.arange(xmin, xmax, offsetx), list(reversed(np.arange(ymin, ymax, offsety))))
        xc = xx.flatten()
        yc = yy.flatten()
        points = np.dstack((xx, yy))


        points = []
        for x, y in zip(xc, yc):
            polygon_rectangle = Polygon(
                [[x - offsetx, y - offsety], [x + offsetx, y - offsety], [x + offsetx, y + offsety],
                 [x - offsetx, y + offsety], [x - offsetx, y - offsety]])

            if (polygon_rectangle.intersection(polygon_area).area / polygon_rectangle.area) >= 0.2:
                points.append((y, x))

        return points

    def __add_scroll_index(self, m, points):

        text_index = BoundedIntText(value=1, min=0, max=len(points), layout=Layout(width='50px', height='30px'))
        recenter_button = Button(disabled=False, button_style='', tooltip='Recenter the map', icon='arrows',
                                 layout=Layout(width='30px', height='30px'))

        def recenter_on_click(b):
            change_center(text_index.value)
            if not self.result_btn is None:
                self.result_btn.value = "Both"

        def change_center(number):
            m.center = points[number]
            m.zoom = 18

        def observe_change(w):
            if w["name"] == "value":
                change_center(w["new"])

        text_index.observe(observe_change)

        recenter_button.on_click(recenter_on_click)

        index_control = WidgetControl(widget=HBox([text_index, recenter_button]), position='topleft')

        m.add_control(index_control)
        text_index.value = 0

