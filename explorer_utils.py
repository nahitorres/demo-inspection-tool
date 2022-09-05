import os
import json
from enum import Enum
from ipyleaflet import  TileLayer, GeoJSON, Popup,LayerGroup, LegendControl
from collections import defaultdict
from geojson import FeatureCollection
from ipywidgets.widgets import HTML
from shapely.geometry import shape

class ColorConfidence(Enum):
    LOW = "#e5f505"
    VERY_LOW = "#c9d2bc"
    MEDIUM = "#f4ba10"
    HIGH = "#ae2d2d"
    
############## ADD SATELLITE LAYERS TO MAP ############
def get_ortophoto_layer():
    token = 'TOKEN...'
    return TileLayer(
        url='http://otprovider.wdscoml.it/tiles/{z}/{x}/{y}.png?token=' + token,
        name='Orthophoto',
        visible=True,
        max_zoom=22
    )

def get_google_layer():
    return TileLayer(
        url='http://mt0.google.com/vt/lyrs=y&hl=en&x={x}&y={y}&z={z}',
        name='Google Map',
        attribution='Google',
        visible=True,
        max_zoom=22
    )

def add_impianti_layer(m, path):

    ## Download from server instead of this
    with open(path, "r") as file:
        impianti_json = json.load(file)

    impianti_layer = GeoJSON(data=impianti_json, hover_style={'fill-color': '#ff05d5', 'color': '#ff05d5','marker-color': '#ff05d5'})
    m.add_layer(impianti_layer)
    return impianti_layer

def add_cams_layer(m, cams_path):

    ## Download from server instead of this
    with open(cams_path, "r") as cams_f:
        cams_json = json.load(cams_f)

    cams_layer = GeoJSON(data=cams_json, hover_style={'dashArray': '10', 'fill': 0})
    m.add_layer(cams_layer)
    return cams_layer

################ PREDICTIONS LAYERS ################

def get_color( score):
    if score >= 0.8:
        return ColorConfidence.HIGH
    elif score >= 0.5:
        return ColorConfidence.MEDIUM
    elif score >= 0.3:
        return ColorConfidence.LOW
    elif score >= 0.2:
        return ColorConfidence.VERY_LOW

def get_color_legend():
    return LegendControl({">.8":ColorConfidence.HIGH.value,">.5":ColorConfidence.MEDIUM.value, ">.3":ColorConfidence.LOW.value, ">.2":ColorConfidence.VERY_LOW.value}, name="Pred", position="bottomright")

    
def add_prediction_layer(m, preds_file_path, show_pred_score):
    with open(preds_file_path, "r") as file:
        pred_json = json.load(file)

    message = HTML()
    message.value = ""
    popup = Popup(child=message, close_button=True, auto_close=True, close_on_escape_key=True, keep_in_view=True)

    def click_handler_pred(event=None, feature=None, id=None, properties=None):

        if popup in m.layers:
            m.remove_layer(popup)
        s = shape(feature["geometry"])
        popup.location = s.centroid.y, s.centroid.x

        message.value = "Prediction {:.2f}<br/>Area_ID: {}<br/><a target='_blank' href='https://www.google.it/maps/@{},{},250m/data=!3m1!1e3'>Link</a>".format(
            properties["score"], os.path.basename(properties["path"])[:-4], s.centroid.y, s.centroid.x)
        popup.child = message

        m.add_layer(popup)

    confidence_layers = defaultdict(list)
    for feature in pred_json["features"]:
        confidence_layers[get_color(feature["properties"]["score"])].append(feature)

    pred_layers = []
    for key in confidence_layers:
        # if key == ColorConfidence.VERY_LOW:
        #    continue
        layer = GeoJSON(data=FeatureCollection(confidence_layers[key]),
                        style={'fillOpacity': 0.1, 'color': key.value,
                               'fill-color': key.value})  # , hover_style={"fill":0})
        if show_pred_score:
            layer.on_click(click_handler_pred)
        pred_layers.append(layer)

    layer_group = LayerGroup(layers=pred_layers)
    m.add_layer(layer_group)
    return layer_group
