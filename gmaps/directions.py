
import ipywidgets as widgets
import warnings

from traitlets import Bool, Unicode, CUnicode, List, Enum, observe, validate

from . import geotraitlets
from .locations import locations_to_list
from .maps import GMapsWidgetMixin


ALLOWED_TRAVEL_MODES = {'BICYCLING', 'DRIVING', 'TRANSIT', 'WALKING'}
DEFAULT_TRAVEL_MODE = 'DRIVING'


def _warn_obsolete_data():
    warnings.warn(
        'The "data" traitlet is deprecated, and will be '
        'removed in jupyter-gmaps 0.9.0. '
        'Use "locations" instead.', DeprecationWarning)


def _warn_obsolete_waypoints():
    warnings.warn(
        'Passing "None" to waypoints is deprecated, and will be '
        'removed in jupyter-gmaps 0.9.0. '
        'Pass an empty list.', DeprecationWarning)


class DirectionsServiceException(RuntimeError):
    pass


class Directions(GMapsWidgetMixin, widgets.Widget):
    """
    Directions layer.

    Add this to a :class:`gmaps.Figure` instance to draw directions.

    Use the :func:`gmaps.directions_layer` factory function to
    instantiate this class, rather than the constructor.

    :Examples:

    >>> fig = gmaps.figure()
    >>> start = (46.2, 6.1)
    >>> end = (47.4, 8.5)
    >>> waypoints = [(52.37403, 4.88969)]
    >>> directions_layer = gmaps.directions_layer(start, end, waypoints)
    >>> fig.add_layer(directions_layer)

    There is a limitation in the number of waypoints allowed by Google
    (currently 23). If it
    fails to return directions, a ``DirectionsServiceException`` is raised.

    >>> directions_layer = gmaps.Directions(data=data*10)
    Traceback (most recent call last):
        ...
    DirectionsServiceException: No directions returned: MAX WAYPOINTS EXCEEDED

    :param data: List of (latitude, longitude) pairs denoting a single
        point. The first pair denotes the starting point and the last pair
        denote the end of the route.
        Latitudes are expressed as a float between -90
        (corresponding to 90 degrees south) and +90 (corresponding to
        90 degrees north). Longitudes are expressed as a float
        between -180 (corresponding to 180 degrees west) and 180
        (corresponding to 180 degrees east).
    :type data: list of tuples of length >= 2

    :param travel_mode:
        Choose the mode of transport. One of ``'BICYCLING'``, ``'DRIVING'``,
        ``'WALKING'`` or ``'TRANSIT'``. A travel mode of ``'TRANSIT'``
        indicates public transportation. Defaults to ``'DRIVING'``.
    :type travel_mode: str, optional

    :param avoid_ferries: Avoids ferries where possible.
    :type avoid_ferries: bool, optional

    :param avoid_highways: Avoids highways where possible.
    :type avoid_highways: bool, optional

    :param avoid_tolls: Avoids toll roads where possible.
    :type avoid_tolls: bool, optional

    :param optimize_waypoints: Attempt to re-order the supplied intermediate
        waypoints to minimize overall cost of the route.
    :type optimize_waypoints: bool, optional
    """
    has_bounds = True
    _view_name = Unicode("DirectionsLayerView").tag(sync=True)
    _model_name = Unicode("DirectionsLayerModel").tag(sync=True)

    start = geotraitlets.Point().tag(sync=True)
    end = geotraitlets.Point().tag(sync=True)
    waypoints = geotraitlets.LocationArray().tag(sync=True)
    data = List(minlen=2, allow_none=True, default_value=None)
    data_bounds = List().tag(sync=True)
    avoid_ferries = Bool(default_value=False).tag(sync=True)
    avoid_highways = Bool(default_value=False).tag(sync=True)
    avoid_tolls = Bool(default_value=False).tag(sync=True)
    optimize_waypoints = Bool(default_value=False).tag(sync=True)
    travel_mode = Enum(
            ALLOWED_TRAVEL_MODES,
            default_value=DEFAULT_TRAVEL_MODE
    ).tag(sync=True)

    layer_status = CUnicode().tag(sync=True)

    def __init__(self, start=None, end=None, waypoints=None, **kwargs):
        if kwargs.get('data') is not None:
            _warn_obsolete_data()
            # Keep for backwards compatibility with data argument
            data = kwargs['data']
            waypoints = kwargs.get('waypoints')
            if start is None and end is None and waypoints is None:
                start, end, waypoints = Directions._destructure_data(data)
                kwargs.update(
                    dict(start=start, end=end, waypoints=waypoints, data=None))
            else:
                raise ValueError(
                    'Cannot set both data and one of "start", "end"'
                    'or "waypoints".')
        else:
            if waypoints is None:
                _warn_obsolete_waypoints()
                waypoints = []
            kwargs.update(dict(start=start, end=end, waypoints=waypoints))
        super(Directions, self).__init__(**kwargs)

    @staticmethod
    def _destructure_data(data):
        start = data[0]
        end = data[-1]
        waypoints = data[1:-1]
        return start, end, waypoints

    @validate('waypoints')
    def _valid_waypoints(self, proposal):
        print('validating')
        if proposal['value'] is None:
            _warn_obsolete_waypoints()
            proposal['value'] = []
        return proposal['value']

    @observe('data')
    def _on_data_change(self, change):
        data = change['new']
        if data is not None:
            _warn_obsolete_data()
            with self.hold_trait_notifications():
                self.start, self.end, self.waypoints = \
                        self._destructure_data(data)

    @observe('start', 'end', 'waypoints')
    def _calc_bounds(self, change):
        all_data = [self.start] + self.waypoints + [self.end]
        min_latitude = min(row[0] for row in all_data)
        min_longitude = min(row[1] for row in all_data)
        max_latitude = max(row[0] for row in all_data)
        max_longitude = max(row[1] for row in all_data)
        self.data_bounds = [
            (min_latitude, min_longitude),
            (max_latitude, max_longitude)
        ]

    @observe("layer_status")
    def _handle_layer_status(self, change):
        if change["new"] != "OK":
            raise DirectionsServiceException(
                "No directions returned: " + change["new"])


def directions_layer(
        start, end, waypoints=None, avoid_ferries=False,
        travel_mode=DEFAULT_TRAVEL_MODE,
        avoid_highways=False, avoid_tolls=False, optimize_waypoints=False):
    """
    Create a directions layer.

    Add this layer to a :class:`gmaps.Figure` instance to draw
    directions on the map.

    :Examples:

    >>> fig = gmaps.figure()
    >>> start = (46.2, 6.1)
    >>> end = (47.4, 8.5)
    >>> directions = gmaps.directions_layer(start, end)
    >>> fig.add_layer(directions)
    >>> fig

    You can also add waypoints on the route:

    >>> waypoints = [(46.4, 6.9), (46.9, 8.0)]
    >>> directions = gmaps.directions_layer(start, end, waypoints=waypoints)

    You can choose the travel mode:

    >>> directions = gmaps.directions_layer(start, end, travel_mode='WALKING')

    :param start:
        (Latitude, longitude) pair denoting the start of the journey.
    :type start: 2-element tuple

    :param end:
        (Latitude, longitude) pair denoting the end of the journey.
    :type end: 2-element tuple

    :param waypoints:
        Iterable of (latitude, longitude) pair denoting waypoints.
        Google maps imposes a limitation on the total number of waypoints.
        This limit is currently 23. You cannot use waypoints when the
        travel_mode is ``'TRANSIT'``.
    :type waypoints: List of 2-element tuples, optional

    :param travel_mode:
        Choose the mode of transport. One of ``'BICYCLING'``, ``'DRIVING'``,
        ``'WALKING'`` or ``'TRANSIT'``. A travel mode of ``'TRANSIT'``
        indicates public transportation. Defaults to ``'DRIVING'``.
    :type travel_mode: str, optional

    :param avoid_ferries:
        Avoid ferries where possible.
    :type avoid_ferries: bool, optional

    :param avoid_highways:
        Avoid highways where possible.
    :type avoid_highways: bool, optional

    :param avoid_tolls:
        Avoid toll roads where possible.
    :type avoid_tolls: bool, optional

    :param optimize_waypoints:
        If set to true, will attempt to re-order the supplied intermediate
        waypoints to minimize overall cost of the route.
    :type optimize_waypoints: bool, optional
    """
    kwargs = {
        "start": start,
        "end": end,
        "waypoints": waypoints,
        "travel_mode": travel_mode,
        "avoid_ferries": avoid_ferries,
        "avoid_highways": avoid_highways,
        "avoid_tolls": avoid_tolls,
        "optimize_waypoints": optimize_waypoints
    }
    return Directions(**kwargs)
