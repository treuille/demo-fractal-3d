import streamlit as st
import random
import math
import plotly.graph_objects as go
import numpy as np
import collections

refinement_types = [
    # Create a symmetric fractal mesh
    'fractal',
    
    # Create a planet-like fractal
    'planet'
]

@st.cache
def create_octahedron():
    """Returns a "unit octahedron" as the tuple
    (vertices, faces)"""
    
    vertices = np.array([
        (  1,  0,  0),  # 0
        (  0,  1,  0),  # 1
        (  0,  0,  1),  # 2
        ( -1,  0,  0),  # 3
        (  0, -1,  0),  # 4
        (  0,  0, -1)], # 5
        dtype=np.float64)

    faces = np.array([
        (0, 1, 2),
        (1, 3, 2),
        (3, 4, 2),
        (4, 0, 2),
        (0, 5, 1),
        (1, 5, 3),
        (3, 5, 4),
        (4, 5, 0)],
        dtype=np.int)
    
    return vertices, faces

def fractal_interpolate(vec_1, vec_2, factor=1.0):
    if type(factor) == tuple:
        factor = random.uniform(*factor)
    factor_1 = np.linalg.norm(vec_1)
    factor_2 = np.linalg.norm(vec_2)
    midpoint_vec = 0.5 * (vec_1 + vec_2)
    midpoint_factor = 0.5 * (factor_1 + factor_2)
    unit_vec = midpoint_vec / np.linalg.norm(midpoint_vec)
    return unit_vec * midpoint_factor * factor

def split_vertex(vertex_1, vertex_2, vertices, splits, interpolate):
    """Returns the index of a vertex halfway between vertex_1
    and vertex_2. If the vertex doesn't exist, then add it
    to the list of vertices. The splits table keeps track of all
    the split vertices."""
    if vertex_1 > vertex_2:
        vertex_1, vertex_2 = vertex_2, vertex_1
    split_vertex = splits.get((vertex_1, vertex_2), None)
    if split_vertex == None:
        split_vertex = len(vertices)
        vec_1 = vertices[vertex_1]
        vec_2 = vertices[vertex_2]
        new_vertex = interpolate(vec_1, vec_2)
        vertices.append(new_vertex)
        splits[(vertex_1, vertex_2)] = split_vertex
    return split_vertex

def refine_mesh(vertices, faces, interpolate):
    """Takes a list of vertices and faces and returns a new pair
    (vertices, faces) by subdividing each face 4X."""
    # mapping from (vertex_a, vertex_b) -> vertex_c
    # where vertex_c is halfway between vertex_a and vertex_b
    splits = {}

    new_vertices = list(vertices)
    new_faces = []
    for (a, b, c) in faces:
        a_b = split_vertex(a, b, new_vertices, splits, interpolate) 
        b_c = split_vertex(b, c, new_vertices, splits, interpolate) 
        c_a = split_vertex(c, a, new_vertices, splits, interpolate) 
        new_faces.extend([
            (c_a,   a, a_b),
            (a_b,   b, b_c),
            (b_c,   c, c_a),
            (a_b, b_c, c_a)
        ])

    return np.array(new_vertices), np.array(new_faces)

def to_mesh_3d(vertices, faces, colorscale=None):
    """Convert a list of vertices and faces to plotly mesh."""
    
    # Use the default colorscale if none is specified
    if colorscale == None:
        colorscale = [
            (0.0, 'rgb(0, 0, 55)'),
            (1.0, 'rgb(255, 255, 0)'),
        ]

    return go.Mesh3d(
        # 8 vertices of a cube
        x=vertices[:,0],
        y=vertices[:,1],
        z=vertices[:,2],
        colorbar_title='z',

        # The intensity is based on the distance
        intensity=np.linalg.norm(vertices, axis=1),
        colorscale=colorscale,

        # i, j and k give the vertices of triangles
        i=faces[:,0],
        j=faces[:,1],
        k=faces[:,2],
        name='y',
        showscale=False,
        flatshading=True,
     )

def to_fig(mesh_3d):
    """Convert a plotly mesh to a plotly figure."""
    dont_show_background = { 'visible': False }
    layout = go.Layout(
        height=800,
        scene={
            'xaxis': dont_show_background,
            'yaxis': dont_show_background,
            'zaxis': dont_show_background,
        })
    return go.Figure(data=[mesh_3d], layout=layout)

def fractal_refinement():
    # Refine the mesh a certain number of times.
    vertices, faces = create_octahedron()
    refinements = st.sidebar.number_input('refinements', 0, 9, 1)
    for i in range(refinements):
        x = st.sidebar.slider(f'overshoot {i}', 0.0, 2.0, 1.0)
        def interpolate(v1, v2): 
            return fractal_interpolate(v1, v2, factor=(x, x))
        vertices, faces = refine_mesh(vertices, faces, interpolate)
    return vertices, faces

def planet_refinement():
    # Refine the mesh a certain number of times.
    refinements = st.sidebar.number_input('refinements', 0, 9, 6)
    offset_range = st.sidebar.slider('offset range', 0.0, 1.0, 0.05)
    dampen = st.sidebar.slider('dampening', 0.0, 1.0, 0.92)
    return cached_planet(refinements, offset_range, dampen)

@st.cache(show_spinner=False)
def cached_planet(refinements, offset_range, dampen): 
    vertices, faces = create_octahedron()
    for i in range(refinements):
        factor_range = (
            1.0 - offset_range * (dampen ** i),
            1.0 + offset_range * (dampen ** i),
        )
        def interpolate(v1, v2): 
            return fractal_interpolate(v1, v2, factor=factor_range)
        vertices, faces = refine_mesh(vertices, faces, interpolate)
    return vertices, faces 

def planet_colorscale():
    ColorPreset = collections.namedtuple('ColorPreset', 'name elevation color')
    COLOR_PRESETS = [
            ColorPreset(name='ocean', elevation=0.45, color=(0, 0, 128)),
        ColorPreset(name='beach', elevation=0.46, color=(255, 255, 0)),
        ColorPreset(name='forest', elevation=0.47, color=(0, 128, 0)),
        ColorPreset(name='mountain', elevation=0.87, color=(200, 200, 200)),
        ColorPreset(name='moutaintop', elevation=1.0, color=(255, 255, 255)),
    ]

    colorscale = []
    for name, elevation, color in COLOR_PRESETS:
        st.sidebar.subheader(name)
        elevation = st.sidebar.slider(f'{name} elevation', 0.0, 1.0, elevation)
        color = st.sidebar.beta_color_picker(f'{name} color', '#%02x%02x%02x' % color)
        color = 'rgb(%i, %i, %i)' % tuple(int(color[i:i+2], 16) for i in (1, 3, 5))
        if not colorscale:
            colorscale.append((0.0, color))
        colorscale.append((elevation, color))

    return colorscale

def main():
    """Execution starts here."""
    # Create the base shape
    refinement = st.sidebar.selectbox('Refinement type',
            refinement_types[::-1])
    if refinement == 'fractal':
        vertices, faces = fractal_refinement()
        colorscale = None # default colors
    elif refinement == 'planet':
        vertices, faces = planet_refinement()
        colorscale = planet_colorscale()
    else:
        raise RuntimeError(f'Refinement "{refinement}" not understood.')

    # Convert this to a plotly figure.
    mesh_3d = to_mesh_3d(vertices, faces, colorscale)
    fig = to_fig(mesh_3d)

    # Display the output 
    "# Fractal Exploration"
    st.write(fig)

if __name__ == '__main__':
    main()
