# The MIT License (MIT)
# Copyright (c) 2016, 2017 by the ESA CCI Toolbox development team and contributors
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
Description
===========

Operations for resources of type pandas.DataFrame, geopandas.GeoDataFrame and cate.core.types.GeoDataFrame which all
form (Feature) Attribute Tables (FAT).

Functions
=========
"""
import geopandas as gpd
import pandas as pd

from cate.core.op import op, op_input
from cate.core.types import VarName, DataFrameLike, GeometryLike


@op(tags=['filter'], version='1.0')
@op_input('df', data_type=DataFrameLike)
@op_input('var', value_set_source='df', data_type=VarName)
def data_frame_min(df: DataFrameLike.TYPE, var: VarName.TYPE) -> pd.DataFrame:
    """
    Select the first record of a data frame for which the given variable value is minimal.

    :param df: The data frame or dataset.
    :param var: The variable.
    :return: A new, one-record data frame.
    """
    data_frame = DataFrameLike.convert(df)
    var_name = VarName.convert(var)
    row_index = data_frame[var_name].idxmin()
    row_frame = data_frame.loc[[row_index]]
    return _maybe_convert_to_geo_data_frame(data_frame, row_frame)


@op(tags=['filter'], version='1.0')
@op_input('df', data_type=DataFrameLike)
@op_input('var', value_set_source='df', data_type=VarName)
def data_frame_max(df: DataFrameLike.TYPE, var: VarName.TYPE) -> pd.DataFrame:
    """
    Select the first record of a data frame for which the given variable value is maximal.

    :param df: The data frame or dataset.
    :param var: The variable.
    :return: A new, one-record data frame.
    """
    data_frame = DataFrameLike.convert(df)
    var_name = VarName.convert(var)
    row_index = data_frame[var_name].idxmax()
    row_frame = data_frame.loc[[row_index]]
    return _maybe_convert_to_geo_data_frame(data_frame, row_frame)


@op(tags=['filter'], version='1.0')
@op_input('df', data_type=DataFrameLike)
@op_input('query_expr')
def data_frame_query(df: DataFrameLike.TYPE, query_expr: str) -> pd.DataFrame:
    """
    Select records from the given data frame where the given conditional query expression evaluates to "True".

    If the data frame *df* contains a geometry column (a ``GeoDataFrame`` object),
    then the query expression *query_expr* can also contain geometric relationship tests,
    for example the expression ``"population > 100000 and @within('-10, 34, 20, 60')"``
    could be used on a data frame with the *population* and a *geometry* column
    to query for larger cities in West-Europe.

    The geometric relationship tests are
    * ``@almost_equals(geom)`` - does a feature's geometry almost equal the given ``geom``;
    * ``@contains(geom)`` - does a feature's geometry contain the given ``geom``;
    * ``@crosses(geom)`` - does a feature's geometry cross the given ``geom``;
    * ``@disjoint(geom)`` - does a feature's geometry not at all intersect the given ``geom``;
    * ``@intersects(geom)`` - does a feature's geometry intersect with given ``geom``;
    * ``@touches(geom)`` - does a feature's geometry have a point in common with given ``geom`` but does not intersect it;
    * ``@within(geom)`` - is a feature's geometry contained within given ``geom``.

    The *geom* argument may be a point ``"<lon>, <lat>"`` text string,
    a bounding box ``"<lon1>, <lat1>, <lon2>, <lat2>"`` text, or any valid geometry WKT.

    :param df: The data frame or dataset.
    :param query_expr: The conditional query expression.
    :return: A new data frame.
    """
    data_frame = DataFrameLike.convert(df)

    local_dict = dict(from_wkt=GeometryLike.convert)
    if hasattr(data_frame, 'geometry') and isinstance(data_frame.geometry, gpd.GeoSeries):
        def _almost_equals(geometry: GeometryLike):
            return _data_frame_geometry_op(data_frame.geometry.geom_almost_equals, geometry)

        def _contains(geometry: GeometryLike):
            return _data_frame_geometry_op(data_frame.geometry.contains, geometry)

        def _crosses(geometry: GeometryLike):
            return _data_frame_geometry_op(data_frame.geometry.crosses, geometry)

        def _disjoint(geometry: GeometryLike):
            return _data_frame_geometry_op(data_frame.geometry.disjoint, geometry)

        def _intersects(geometry: GeometryLike):
            return _data_frame_geometry_op(data_frame.geometry.intersects, geometry)

        def _touches(geometry: GeometryLike):
            return _data_frame_geometry_op(data_frame.geometry.touches, geometry)

        def _within(geometry: GeometryLike):
            return _data_frame_geometry_op(data_frame.geometry.within, geometry)

        local_dict['almost_equals'] = _almost_equals
        local_dict['contains'] = _contains
        local_dict['crosses'] = _crosses
        local_dict['disjoint'] = _disjoint
        local_dict['intersects'] = _intersects
        local_dict['touches'] = _touches
        local_dict['within'] = _within

    data_frame_subset = data_frame.query(query_expr,
                                         truediv=True,
                                         local_dict=local_dict,
                                         global_dict={})

    return _maybe_convert_to_geo_data_frame(data_frame, data_frame_subset)


def _data_frame_geometry_op(instance_method, geometry: GeometryLike):
    geometry = GeometryLike.convert(geometry)
    return instance_method(geometry)


def _maybe_convert_to_geo_data_frame(data_frame: pd.DataFrame, data_frame_2: pd.DataFrame) -> pd.DataFrame:
    if isinstance(data_frame, gpd.GeoDataFrame) and not isinstance(data_frame_2, gpd.GeoDataFrame):
        return gpd.GeoDataFrame(data_frame_2, crs=data_frame.crs)
    else:
        return data_frame_2
