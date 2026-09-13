param(
  [Parameter(Mandatory=$true)]
  [string]$ApiKey,
  [string]$Episodes = "4 5 6 7",
  [string]$ReferenceUrls = ""
)

$env:OFOX_API_KEY = $ApiKey
$env:OFOX_VIDEO_MODEL = "bytedance/seedance-2.0-mini"
$env:OFOX_RESOLUTION = "720p"
$env:OFOX_PROVIDER = "byteplus"
if ($ReferenceUrls) { $env:JASMINE_SAM_REFERENCE_URLS = $ReferenceUrls }

$eps = $Episodes -split "\s+" | Where-Object { $_ -ne "" }
python tools/jasmine_sam_generate.py @eps
