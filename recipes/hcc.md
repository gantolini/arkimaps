# hcc: High Cloud Cover

Mixer: **default**

## Inputs

* **hcc**:
    * **Option 1**:
        * **Arkimet matcher**: `product:GRIB1,,2,75`
        * **grib_filter matcher**: `shortName is "clch"`
        * **mgrib {k}**: `False`
        * **mgrib {k}**: `0.08`
    * **Option 2**:
        * **Arkimet matcher**: `product:GRIB1,,2,75`
        * **grib_filter matcher**: `shortName is "clch"`
        * **mgrib {k}**: `False`
        * **mgrib {k}**: `0.08`

## Steps

### add_basemap

Add a base map

With arguments:
```
{
  "params": {
    "subpage_map_projection": "cylindrical",
    "subpage_lower_left_longitude": -5.0,
    "subpage_lower_left_latitude": 30.0,
    "subpage_upper_right_longitude": 27.0,
    "subpage_upper_right_latitude": 55.0
  }
}
```

### add_coastlines_bg

Add background coastlines


### add_grib

Add a grib file

With arguments:
```
{
  "name": "hcc"
}
```

### add_contour

Add contouring of the previous data

With arguments:
```
{
  "params": {
    "contour": false,
    "contour_highlight": false,
    "contour_hilo": false,
    "contour_label": false,
    "contour_level_list": [
      1.0,
      2.0,
      3.0,
      4.0,
      5.0,
      6.0,
      7.0,
      8.0
    ],
    "contour_min_level": 4.0,
    "contour_max_level": 8.0,
    "contour_level_selection_type": "level_list",
    "contour_shade": true,
    "contour_shade_max_level_colour": "rgba(0,188,0,0.4)",
    "contour_shade_min_level_colour": "rgba(0,188,0,0.0)",
    "contour_shade_method": "area_fill",
    "contour_interpolation_ceiling": 7.99,
    "legend": true,
    "legend_title": true,
    "legend_title_text": "High cloud cover [okta]"
  }
}
```

### add_coastlines_fg

Add foreground coastlines


### add_grid

Add a coordinates grid


### add_boundaries

Add a coordinates grid

