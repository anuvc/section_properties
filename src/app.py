from dash import Dash, dcc, html, Input, Output, State, callback

from gaudi import preprocessing, polygonize, section_properties, meshing
import skimage.io as io
import datetime
import base64
import diskcache
from dash.long_callback import DiskcacheLongCallbackManager

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

# setup diskcache for caching output from gmsh: gmsh initialize() is not thread-safe
cache = diskcache.Cache('./cache')
lcm = DiskcacheLongCallbackManager(cache)

app = Dash(__name__, long_callback_manager=lcm, external_stylesheets=external_stylesheets)
server = app.server

# defaults
minimum_connected_pixels = 50
minimum_conrner_angle = 15
bbox_x = 100
bbox_y = 100
mesh_size = 10
extrude = None

app.layout = html.Div([
    dcc.Upload(
        id='upload-image',
        children=html.Div([
            'Drag and Drop or ',
            html.A('Select Files')
        ]),
        style={
            'width': '100%',
            'height': '60px',
            'lineHeight': '60px',
            'borderWidth': '1px',
            'borderStyle': 'dashed',
            'borderRadius': '5px',
            'textAlign': 'center',
            'margin': '10px'
        },
        # Allow multiple files to be uploaded
        multiple=True
    ),
    html.Div(id='output-image-upload'),
    html.Div(id='output-section-properties', style={'whiteSpace': 'pre-line'})
])

def parse_contents(contents, filename, date):
    return html.Div([
        html.H5(filename),
        html.H6(datetime.datetime.fromtimestamp(date)),

        # HTML images accept base64 encoded strings in the same format
        # that is supplied by the upload
        html.Img(src=contents),
        html.Hr(),
        html.Div('Raw Content'),
        html.Pre(contents[0:200] + '...', style={
            'whiteSpace': 'pre-wrap',
            'wordBreak': 'break-all'
        })
    ])

@callback(Output('output-image-upload', 'children'),
              Input('upload-image', 'contents'),
              State('upload-image', 'filename'),
              State('upload-image', 'last_modified'))
def update_output(list_of_contents, list_of_names, list_of_dates):
    if list_of_contents is not None:
        children = [
            parse_contents(c, n, d) for c, n, d in
            zip(list_of_contents, list_of_names, list_of_dates)]
        return children
    
@app.long_callback(Output('output-section-properties', 'children'),
              Input('upload-image', 'contents'),
              prevent_intial_call=True)
def update_section_properties(list_of_contents):
    if list_of_contents is None:
        return 'no image uploaded'
    else:
        # get the image
        image = list_of_contents[0]
        # print(image)
        # convert base64 to image
        image = base64.b64decode(image.split(",")[1])
        image = io.imread(image, plugin='imageio')
        print(image)
        skeletonized_image = preprocessing.skeletonize(image)
        polygons = polygonize.get_polygons(
            skeletonized_image, minimum_connected_pixels, minimum_conrner_angle
        )
        polygons = section_properties.scale_polygon(polygons, bbox_x, bbox_y)
        section = polygons[0]
        print(f"approximate section area: {section.area}")
        print(f"approximate section centroid: {section.centroid}")
        centroid = [section.centroid.coords.xy[0][0], section.centroid.coords.xy[1][0]]
        mesh = meshing.generate_mesh_from_polygons(polygons, mesh_size, extrude)
        Ix, Iy = section_properties.calculate_area_moment_of_inertia(mesh, centroid)
        print(f"Area Moment of Inertia about X: {Ix}")
        print(f"Area Moment of Inertia about Y: {Iy}")
        text = "approximate section area: " + str(section.area) + "\n" + "approximate section centroid: " + str(section.centroid) + "\n" + "Area Moment of Inertia about X: " + str(Ix) + "\n" + "Area Moment of Inertia about Y: " + str(Iy)
    return text

if __name__ == '__main__':
    app.run(debug=True)