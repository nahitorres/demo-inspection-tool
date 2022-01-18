# Inspect tool (for illegal ladnfills detection)

The Inspector Tool that can help the illegal landfill detection process through a data visualization GUI. The GUI provides an effective visualization of the predictions of a trainned CNN. The Tool is based on Jupyter Notebook and presents the users with an interface to visualize the predictions of the model in the map. 

**The main uses cases the tool addresses are include:**

_Select the area to analyze._ The analyst selects the area to analyze by means of a GeoJson file containing the boundaries of the region.
    
_Select the map source._ The analyst can choose among the different available sources: orthophotos from campaigns conducted in different times (now it works with campaigns done in the years 2015 or 2018), or images from Google Maps. Each layer provides different information. For example, the Google Maps layer provides   street names and references to different points of interest, which can be useful to better understand the context.  On the other hand, orthophotos from different years allow the analysts to see if a suspicious location extended or shrunk over the years. - The ortophoto providers url for such layers might need to be replaced by your own layers.
    
_Move around the map._ The analyst can move around by dragging with the mouse to different positions or by using the iteration functionality. The iteration mode consists of superimposing a grid  over  area under analysis by a given vertical and horizontal offset so that each cell in the grid is assigned a position. Then the analyst can move by changing the grid position (one at a time) with the previous and next commands.  The GUI also offers the usual zoom controls.

_Visualize coordinates of a given point._ The analyst can obtain the coordinates of a given point at any moment, for example, to share or save this location. With a right click on any point in the map a pop up with the coordinates is shown, as well as as the option to open the location on Google Maps or download a Keyhole Markup Language (KML) representation of the location.
    
_Visualize authorized waste treatment sites._ The analyst can choose to see on the map the coordinates of the authorized sites. This could be of great  help to understand the context. Again, this information is reserved, if you want to run it you might replace it with your own information layers.
    
_Visualize CNNs model predictions._ The analyst can display the previously computed model output on the map. The output of the model is shown by means of color coded rectangles, where the color indicates the confidence of the model for the particular scene. Very low confidence predictions (below 0.20) are filtered out.
    
_Visualize CAMs._ The analyst can visualize the CAMs output for the model in the areas were predictions are shown. This can guide the eye to the most relevant spots of the scene and prevent the oversight of suspicious objects. 

_Signal a suspicious site._ The analyst can indicate the presence of a suspicious site by drawing a polygon on the map indicating the area of the illicit. Such location can be later removed if it is confirmed that it does not correspond to an illicit dumping.
    
_Describe a suspicious site._ The analyst can add or modify descriptive information of a suspicious site. The descriptive fields are taken from the current characterization process used by the analysis:  severity detected, certainty index, environmental risk, waste types detected, waste storage mode and a free text input for any additional detail. 

_Export suspicious sites data._ The analyst can choose to export the data generated during the analysis in different formats: a Comma Separated Values file to visualize for example in Excel or a KML to visualize in GIS applications such as QGIS or GoogleEarth. 
    
**Version 2 of the tool will externalize the information layers and the required information to annotate, so as to use it not only for the illegal landfill detection. As for now this is possible with minor modification of the code, in version 2 no code modification will be required for genealize to a use case of your choice.
**
