# import modules
import arcpy
import os
import rasterio
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from arcpy import env
from arcpy.sa import *
import sys

from pandas.core.interchange.from_dataframe import primitive_column_to_ndarray

print("modules imported")

############################################################################
# SET VARIABLES BELOW
############################################################################
raster_folder = r"C:/Users/etyrr/OneDrive/Documents/CU_Grad/MillieWorkflow/data/DEM_forDiff_final/"
polygon_clips = r"C:\Users\etyrr\OneDrive\Documents\CU_Grad\MillieWorkflow\data\polygons\Nevados_polygons_DGA2000.shp"
stats_field = "COD_GLA"
snapRaster = r"C:\Users\etyrr\OneDrive\Documents\CU_Grad\MillieWorkflow\data\SRTM_snapRaster.tif"
baseline_raster = r"C:\Users\etyrr\OneDrive\Documents\CU_Grad\MillieWorkflow\data\DEM_forDiff_final\1954_IGM_dem_alfonso_proj_SRTM_2000_s37_w072_1arc_proj_nuth_x-33.45_y-7.88_z-10.01_align.tif"
outputFolder = "C:/Users/etyrr/OneDrive/Documents/CU_Grad/MillieWorkflow/data/DEM_forDiff_final/output_data/"

############################################################################
# END OF SET VARIABLES
############################################################################

# print and create txt file:
f = open(outputFolder + f"code_output.txt", "a")
sys.stdout = f
print("MODEL OUTPUTS TO BE PRINTED TO THIS DOC")
print(f"\n Baseline Raster: {baseline_raster}")
print(f"\n SnapRaster: {snapRaster}")
print(f"\n Polygons Clips: {polygon_clips}")
print(f"\n Polygon Field: {stats_field}")
print("Differencing: Current Raster - Baseline Raster")
print("PROCESSING STARTS")
print("##########################################################")
# clip to polygons
for filename in os.listdir(raster_folder):
    if filename.endswith('.tif'):
        if filename.endswith('clp.tif'):
            continue

        full_path = os.path.join(raster_folder, filename)
        print(f"\n Processing: {full_path}")

        arcpy.env.snapRaster = snapRaster
        # clip each out and output to new directory
        outExtract = ExtractByMask(full_path, polygon_clips, "INSIDE")
        outExtract.save(outputFolder +  f"{filename[:20]}_clp.tif")
        print(f"{filename} clipped and saved to output directory")


# go through each tiff and subtract from the baseline tiff
for tif in os.listdir(outputFolder):
    if tif.endswith('clp.tif'):
        full_path = os.path.join(raster_folder, tif)
        arcpy.env.snapRaster = snapRaster
        if tif == baseline_raster:
            continue

        # Compute difference
        try:
            current_raster = Raster(os.path.join(outputFolder, tif))
            # print(current_raster)
            Difference = current_raster - Raster(baseline_raster)
        except Exception as ex:
            print(ex)

        # Save result
        output_name = f"{tif[:-4]}_diff.tif"
        output_path = os.path.join(outputFolder, output_name)
        Difference.save(output_path)

        # print(f"Saved: {output_path}")

## run summary stats on all of them
for dif in os.listdir(outputFolder):
    if dif.endswith('diff.tif'):
        full_path = os.path.join(outputFolder, dif)

        # calculate Zonal stats on the raster and te polygons
        outZonalStats = ZonalStatisticsAsTable(polygon_clips, stats_field, full_path, outputFolder + f"{dif[:-4]}_zonalStats.dbf", "DATA")
        # export to csvs
        arcpy.ExportTable_conversion(outputFolder + f"{dif[:-4]}_zonalStats.dbf", outputFolder + f"{dif[:-4]}_zonalStats.csv")

# Filter for the three rasters
raster_files = [f for f in os.listdir(outputFolder) if f.endswith('diff.tif')]
raster_files = sorted(raster_files)[:3]  # use only first 3 if more exist

# Initialize lists to track global vmin, vmax and bounds
all_data = []
all_extents = []

# First pass: collect data and stats
for map in raster_files:
    with rasterio.open(os.path.join(outputFolder, map)) as src:
        data = src.read(1)
        nodata = src.nodata
        if nodata is not None:
            data = np.where(data == nodata, np.nan, data)
        all_data.append(data)
        all_extents.append([
            src.bounds.left,
            src.bounds.right,
            src.bounds.bottom,
            src.bounds.top
        ])

# Determine common vmin, vmax and extent
vmin = np.nanmin([np.nanmin(data) for data in all_data])
vmax = np.nanmax([np.nanmax(data) for data in all_data])
common_extent = [
    min(e[0] for e in all_extents),
    max(e[1] for e in all_extents),
    min(e[2] for e in all_extents),
    max(e[3] for e in all_extents)
]

# Plotting
fig, axes = plt.subplots(1, len(raster_files), figsize=(18, 6))
for ax, map, data in zip(axes, raster_files, all_data):
    div_cmap = plt.get_cmap('RdBu_r')  # or 'seismic' for stronger contrast

    # Ensure symmetric color scale around 0
    abs_max = max(abs(vmin), abs(vmax))
    im = ax.imshow(data, cmap=div_cmap, extent=common_extent, vmin=-abs_max, vmax=abs_max)
    ax.set_title(map)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")

cbar = fig.colorbar(im, ax=axes, location='right', shrink=0.8, pad=0.02)
cbar.set_label('Value')

# Layout tweaks
plt.tight_layout()
plt.subplots_adjust(right=0.75)  # leave room for colorbar
plt.savefig(outputFolder + f"Updated_graphic.png")
plt.show()