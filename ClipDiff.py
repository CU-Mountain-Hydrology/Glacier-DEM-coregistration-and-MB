# import modules
import arcpy
import os
import rasterio
import pandas as pd
import matplotlib.pyplot as plt
from arcpy import env
from arcpy.sa import *
print("modules imported")

############################################################################
# SET VARIABLES BELOW
############################################################################
#if you want to visualize the results, == Y, else== N
maps = "N"

# folder where all rasters are sitting
raster_folder = r"C:/Users/etyrr/OneDrive/Documents/CU_Grad/MillieWorkflow/data/output_coreg_dems/ALL/"

# shapefile that you want to use to clip rasters
polygon_clips = r"C:/Users/etyrr/OneDrive/Documents/CU_Grad/MillieWorkflow/data/inventario_nacional_utm.shp"

# sorting field for glaciers (i.e ID field)
stats_field = "COD_GLA"

snapRaster = raster_folder + "CerroBlanco_projected_raster_SRTM_projected_raster_nuth_x+9.32_y+8.27_z+6.54_align.tif"

# what you are subtracting from 
baseline_raster = snapRaster

# fill this in if you had difference projection in mind 
# projOut =

# where your results will be output
outputFolder = r"C:/Users/etyrr/OneDrive/Documents/CU_Grad/MillieWorkflow/data/output_coreg_dems/process_output/"

############################################################################
# END OF SET VARIABLES
############################################################################

# clip to polygons
for filename in os.listdir(raster_folder):
    if filename.endswith('.tif'):
        if filename.endswith('clp.tif'):
            continue

        full_path = os.path.join(raster_folder, filename)
        print(f"Processing: {full_path}")

        arcpy.env.snapRaster = snapRaster
        # clip each out and output to new directory
        outExtract = ExtractByMask(full_path, polygon_clips, "INSIDE")
        outExtract.save(outputFolder +  f"{filename[:20]}_clp.tif")
        print(f"{filename} clipped and saved to output directory")

print("moving on to differencing the rasters")

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
            Difference = current_raster - Raster(baseline_raster)
        except Exception as ex:
            print(ex)

        # Save result
        output_name = f"{tif[:-4]}_diff.tif"
        output_path = os.path.join(outputFolder, output_name)
        Difference.save(output_path)
        print(f"Saved: {output_path}")

## run summary stats on all of them
for dif in os.listdir(outputFolder):
    if dif.endswith('diff.tif'):
        full_path = os.path.join(outputFolder, dif)

        # calculate Zonal stats on the raster and te polygons
        outZonalStats = ZonalStatisticsAsTable(polygon_clips, stats_field, full_path, outputFolder + f"{dif[:-4]}_zonalStats.dbf", "DATA")
        ## convert to csv
        arcpy.conversion.ExportTable(outputFolder + f"{dif[:-4]}_zonalStats.dbf", outputFolder + f"{dif[:-4]}_zonalStats.csv")

# visualize results
# Open the raster
if  maps == "Y":
    for map in os.listdir(outputFolder):
        if map.endswith('diff.tif'):
            map_path = os.path.join(outputFolder, map)
            print(f"Processing: {map_path}")
            with rasterio.open(map_path) as src:
                raster_data = src.read(1)  # Read the first band
                extent = [src.bounds.left, src.bounds.right, src.bounds.bottom, src.bounds.top]
    
            # Plot it
            plt.clf()
            plt.figure(figsize=(8, 6))
            plt.imshow(raster_data, cmap='viridis', extent=extent)
            plt.colorbar(label='Value')
            plt.title(f"Raster Plot of {map}")
            plt.xlabel("Longitude")
            plt.ylabel("Latitude")
            plt.savefig(os.path.join(outputFolder, f"{map[:-4]}.png"))
            plt.close()
