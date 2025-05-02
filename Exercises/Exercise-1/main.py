import os
from urllib.parse import urlparse
from os.path import basename
from zipfile import ZipFile
import aiohttp
import asyncio
import aiofiles

download_uris = [
    "https://divvy-tripdata.s3.amazonaws.com/Divvy_Trips_2018_Q4.zip",
    "https://divvy-tripdata.s3.amazonaws.com/Divvy_Trips_2019_Q1.zip",
    "https://divvy-tripdata.s3.amazonaws.com/Divvy_Trips_2019_Q2.zip",
    "https://divvy-tripdata.s3.amazonaws.com/Divvy_Trips_2019_Q3.zip",
    "https://divvy-tripdata.s3.amazonaws.com/Divvy_Trips_2019_Q4.zip",
    "https://divvy-tripdata.s3.amazonaws.com/Divvy_Trips_2020_Q1.zip",
    "https://divvy-tripdata.s3.amazonaws.com/Divvy_Trips_2220_Q1.zip",
]

def get_filename(uri_input, final_path):
    """
    Extract the file name at the end of the uri, join it with the destination path
    """
    parsed = urlparse(uri_input)
    file_name = basename(parsed.path)
    destination_path = os.path.join(final_path, file_name)
    return destination_path

def zip_to_csv(zip_file):
    """
    Extract the first .csv from zip_file into its containing folder,
    delete the original zip, and return the full path to the CSV.
    """
    try:
        downloads_dir = os.path.dirname(zip_file)
        with ZipFile(zip_file) as z:
            csv_name = next(name for name in z.namelist() if name.endswith('.csv'))
            extracted_path = z.extract(csv_name, path=downloads_dir)
            csv_file = os.path.abspath(extracted_path)

        os.remove(zip_file)
        return csv_file
    
    except StopIteration:
        print(f"No CSV found in {zip_file}")
        return None
    except Exception as e:
        print(f"Error processing {zip_file}: {e}")
        return None

async def download_file(session, url, downloads_path):
    """Download a file asynchronously"""
    zip_path = get_filename(url, downloads_path)
    
    try:
        async with session.get(url) as response:
            if response.status == 200:
                async with aiofiles.open(zip_path, mode='wb') as f:
                    await f.write(await response.read())
                print(f'Successfully downloaded: {zip_path}')
                
                # Process the zip file
                csv_path = zip_to_csv(zip_path)
                if csv_path:
                    print(f'Extracted CSV: {csv_path}')
                    return csv_path
            else:
                print(f"Download failed: {response.status} {response.reason}")
            return None
    except Exception as e:
        print(f'Error downloading {url}: {e}')
        return None

async def async_main():
    downloads_path = 'downloads'
    os.makedirs(downloads_path, exist_ok=True)
    
    async with aiohttp.ClientSession() as session:
        tasks = [
            download_file(session, uri, downloads_path) 
            for uri in download_uris
        ]
        results = await asyncio.gather(*tasks)
        successful_results = [r for r in results if r is not None]
        return successful_results

if __name__ == "__main__":
    results = asyncio.run(async_main())
    print(f"Downloaded and extracted {len(results)} CSVs")
