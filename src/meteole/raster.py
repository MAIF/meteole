"""Functionnalities to deal with the raster data"""
from typing import Optional

import cartopy.crs as ccrs
import matplotlib.pyplot as plt
import rasterio
from cartopy import feature


def open_tiff_file(filename):
    """Ope, a tiff file."""
    with rasterio.open(filename) as source:
        field = source.read(1, masked=True)
        transform = source.transform
    return field, transform


def plot_tiff_file(
    filename,
    data_type: str,
    unit: str,
    title: Optional[str] = None,
):
    """
    Plot a tiff file.

    Parameters
    ----------
    filename : file
       filename from a get coverage
    data_type: str
        datatype of the coverage : temperature,wind,humidity ...
    unit: str
        Unit of the coverage (°C, Kmh)
    title: str, optional
        Plot title

    .. note::
        This Function is more an "How-To" rather than a tool to use as is.

    """
    data_field, transform = open_tiff_file(filename=filename)
    fig = plt.figure(figsize=(10, 10))
    ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
    im = ax.imshow(
        data_field,
        cmap="jet",
        extent=[
            transform[2],
            transform[2] + transform[0] * data_field.shape[1],
            transform[5] + transform[4] * data_field.shape[0],
            transform[5],
        ],
    )
    ax.add_feature(feature.BORDERS.with_scale("10m"), color="black", linewidth=1)
    ax.add_feature(feature.COASTLINE.with_scale("10m"), color="black", linewidth=1)
    cbar = plt.colorbar(im, ax=ax, shrink=0.5)
    height = filename.stem.split("_")[0]
    computed_at = filename.parent.stem.split("_")[-1]

    cbar.set_label(f"{data_type}_{unit}")

    if title is None:
        ax.set_title(f"{data_type} at {height} above ground \n computed at {computed_at} ")
    else:
        ax.set_title(f"{title}_{computed_at}")
    return ax
