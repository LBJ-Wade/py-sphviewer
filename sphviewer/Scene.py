# This file is part of Py-SPHViewer

# <Py-SPHVIewer is a framework for rendering particles in Python
# using the SPH interpolation scheme.>
# Copyright (C) <2013>  <Alejandro Benitez Llambay>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


from __future__ import absolute_import, division, print_function

import numpy as np
import matplotlib.pyplot as plt


def rotate(angle, axis, pos):
    angle *= np.pi/180.0
    if axis == 'x':
        R = np.array([[1, 0, 0],
                      [0, np.cos(angle), np.sin(angle)],
                      [0, -np.sin(angle), np.cos(angle)]])
    elif axis == 'y':
        R = np.array([[np.cos(angle), 0, -np.sin(angle)],
                      [0, 1, 0],
                      [np.sin(angle), 0, np.cos(angle)]])
    elif axis == 'z':
        R = np.array([[np.cos(angle), np.sin(angle), 0],
                      [-np.sin(angle), np.cos(angle), 0],
                      [0, 0, 1]])
    return np.dot(R, pos)


class Scene(object):
    def __init__(self, Particles, Camera=None):
        """
        Scene class takes a sphviewer.Particles class and computes the 
        coordinates of the particles as seen from a Camera. It is to say, 
        for a given particle, whose coordinates are x,y and z, Scene 
        computes a new set of coordinates x' and y', which are the aparent 
        coordinates of the particles as seen from a camera. 
        By default, Camera=None means that Scene have to use an autocamera. It 
        will try to define a Camera whose parameters have some sence according
        to your data set. In case you want to prevent Scene from using an autocamera, 
        you should provide a valid Camera Class.
        As Particles class, Scene has its own getting and setting methods.

        setting methods:
        ----------------

        - set_autocamera
        - update_camera

        getting methods:
        ----------------
        - get_scene
        - get_extent

        other methods are: 

        - plot

        """
        try:
            particles_name = Particles._name
        except AttributeError:
            print("You must use a valid Particles class...")
            return
        if(particles_name != 'PARTICLES'):
            print("You must use a valid Particles class...")
            return

        self._name = 'SCENE'
        self._Particles = Particles

        # I use the autocamera by default
        if(Camera == None):
            from .Camera import Camera
            self.Camera = Camera()
            self.Camera.set_autocamera(Particles)
            self._camera_params = self.Camera.get_params()

        else:
            try:
                camera_name = Camera._name
                if(camera_name != 'CAMERA'):
                    print("You must use a valid Camera class...")
                    print("I will try to set an autocamera...")
                    from .Camera import Camera
                    self.Camera = Camera()
                    self.Camera.set_autocamera(Particles)
                    self._camera_params = self.Camera.get_params()
                else:
                    self.Camera = Camera
                    self._camera_params = self.Camera.get_params()
            except AttributeError:
                print("You must use a valid Camera class...")
                print("I will try to set an autocamera...")
                from .Camera import Camera
                self.Camera = Camera()
                self.Camera.set_autocamera(Particles)
                self._camera_params = self.Camera.get_params()

        self._x, self._y, self._hsml, self._hsml_x, self._hsml_y, self._kview = self.__compute_scene()
        self._m = self._Particles._mass[self._kview]

    def set_autocamera(self, mode='density'):
        """
        - set_autocamera(mode='density'): By default, Scene defines its 
        own Camera. However, there is no a general way for doing so. Scene 
        uses a density criterion for getting the point of view. If this is 
        not a good option for your problem, you can choose among:
        |'minmax'|'density'|'median'|'mean'|. If None of the previous methods
        work well, you may define the camera params by yourself.
        """
        self.Camera.set_autocamera(self._Particles, mode=mode)
        self._camera_params = self.Camera.get_params()
        self._x, self._y, self._hsml, self._hsml_x, self._hsml_y, self._kview = self.__compute_scene()
        self._m = self._Particles._mass[self._kview]

    def get_scene(self):
        """
        - get_scene(): It return the x and y position, the smoothing length 
        of the particles and the index of the particles that are active in 
        the scene. In principle this is an internal function and you don't 
        need this data. 
        """
        return self._x, self._y, self._hsml, self._hsml_x, self._hsml_y, self._m, self._kview

    def get_extent(self):
        """
        - get_extent(): It returns the extent array needed for converting 
        the image coordinates (given in pixels units) into physical coordinates. 
        It is an array like the following one: [xmin,xmax,ymin,ymax]; it is to say, 
        an array that contains the extreme values of the scene. 
        """
        return self.__extent

    def update_camera(self, **kargs):
        """
        - update_camera(**kwarg): By using this method you can define all 
        the new paramenters of the camera. Read the available **kwarg in 
        the sphviewer.Camera documentation. 
        """
        self.Camera.set_params(**kargs)
        self._x, self._y, self._hsml, self._hsml_x, self._hsml_y, self._kview = self.__compute_scene()
        self._m = self._Particles._mass[self._kview]

    def __compute_scene(self):
        from .extensions import scene

        pos  = self._Particles._pos
        hsml = self._Particles._hsml

        # I recast the variables just in case
        xcam = np.float32(self._camera_params['x'])
        ycam = np.float32(self._camera_params['y'])
        zcam = np.float32(self._camera_params['z'])
        theta = np.float32(self._camera_params['t'])
        phi = np.float32(self._camera_params['p'])
        roll = np.float32(self._camera_params['roll'])
        zoom = np.float32(self._camera_params['zoom'])
        xsize = np.int32(self._camera_params['xsize'])
        ysize = np.int32(self._camera_params['ysize'])

        if(self._camera_params['r'] == 'infinity'):
            projection = 0
            print(projection,"infinity")
            rcam = np.float32(0)
            if(self._camera_params['extent'] is None):
                xmin = np.min(pos[:, 0]).astype(np.float32)
                xmax = np.max(pos[:, 0]).astype(np.float32)
                ymin = np.min(pos[:, 1]).astype(np.float32)
                ymax = np.max(pos[:, 1]).astype(np.float32)

                self.__extent = np.array([xmin-xcam,
                                          xmax-xcam,
                                          ymin-ycam,
                                          ymax-ycam], dtype=np.float32)
            else:
                self.__extent = np.float32(self._camera_params['extent'])
                

        elif(self._camera_params['r'] == 'equirectangular'):
            projection = 2
            rcam = np.float32(0)
            self.__extent = np.array([0, 0, 0, 0], dtype=np.float32)            
            
        else:
            projection = 1
            rcam = np.float32(self._camera_params['r'])
            self.__extent = np.array([0, 0, 0, 0], dtype=np.float32)

        xx, yy, hh, hh_x, hh_y, kk = scene.scene(pos[:, 0], pos[:, 1],
                                                 pos[:, 2], hsml, hsml, hsml,
                                                 xcam, ycam, zcam, rcam, theta, phi, roll,
                                                 zoom, self.__extent, xsize, ysize, projection)
            
        return xx, yy, hh, hh_x, hh_y, kk

    def plot(self, axis=None, **kargs):
        """
        - plot(axis=None, **kwarg): Finally, sphviewer.Scene class has its own plotting method. 
        It shows the scene as seen by the camera. It is to say, it plots the particles according
        to their aparent coordinates; axis makes a reference to an existing axis. In case axis is None,
        the plot is made on the current axis.

        The kwargs are :class:`~matplotlib.lines.Line2D` properties:

        agg_filter: unknown
        alpha: float (0.0 transparent through 1.0 opaque)         
        animated: [True | False]         
        antialiased or aa: [True | False]         
        axes: an :class:`~matplotlib.axes.Axes` instance         
        clip_box: a :class:`matplotlib.transforms.Bbox` instance         
        clip_on: [True | False]         
        clip_path: [ (:class:`~matplotlib.path.Path`,         :class:`~matplotlib.transforms.Transform`) |         :class:`~matplotlib.patches.Patch` | None ]         
        color or c: any matplotlib color         
        contains: a callable function         
        dash_capstyle: ['butt' | 'round' | 'projecting']         
        dash_joinstyle: ['miter' | 'round' | 'bevel']         
        dashes: sequence of on/off ink in points         
        data: 2D array (rows are x, y) or two 1D arrays         
        drawstyle: [ 'default' | 'steps' | 'steps-pre' | 'steps-mid' | 'steps-post' ]         
        figure: a :class:`matplotlib.figure.Figure` instance         
        fillstyle: ['full' | 'left' | 'right' | 'bottom' | 'top']         
        gid: an id string         
        label: any string         
        linestyle or ls: [ ``'-'`` | ``'--'`` | ``'-.'`` | ``':'`` | ``'None'`` | ``' '`` | ``''`` ]         and any drawstyle in combination with a linestyle, e.g. ``'steps--'``.         
        linewidth or lw: float value in points         
        lod: [True | False]         
        marker: [ ``7`` | ``4`` | ``5`` | ``6`` | ``'o'`` | ``'D'`` | ``'h'`` | ``'H'`` | ``'_'`` | ``''`` | ``'None'`` | ``' '`` | ``None`` | ``'8'`` | ``'p'`` | ``','`` | ``'+'`` | ``'.'`` | ``'s'`` | ``'*'`` | ``'d'`` | ``3`` | ``0`` | ``1`` | ``2`` | ``'1'`` | ``'3'`` | ``'4'`` | ``'2'`` | ``'v'`` | ``'<'`` | ``'>'`` | ``'^'`` | ``'|'`` | ``'x'`` | ``'$...$'`` | *tuple* | *Nx2 array* ]
        markeredgecolor or mec: any matplotlib color         
        markeredgewidth or mew: float value in points         
        markerfacecolor or mfc: any matplotlib color         
        markerfacecoloralt or mfcalt: any matplotlib color         
        markersize or ms: float         
        markevery: None | integer | (startind, stride)
        picker: float distance in points or callable pick function         ``fn(artist, event)``         
        pickradius: float distance in points         
        rasterized: [True | False | None]         
        snap: unknown
        solid_capstyle: ['butt' | 'round' |  'projecting']         
        solid_joinstyle: ['miter' | 'round' | 'bevel']         
        transform: a :class:`matplotlib.transforms.Transform` instance         
        url: a url string         
        visible: [True | False]         
        xdata: 1D array         
        ydata: 1D array         
        zorder: any number         

        kwargs *scalex* and *scaley*, if defined, are passed on to
        :meth:`~matplotlib.axes.Axes.autoscale_view` to determine
        whether the *x* and *y* axes are autoscaled; the default is
        *True*.

        Additional kwargs: hold = [True|False] overrides default hold state
        """
        if(axis == None):
            axis = plt.gca()
        axis.plot(self.__x, self.__y, 'k.', **kargs)
