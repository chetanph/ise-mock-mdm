import os
import yaml
from fastapi import FastAPI, Response, Query
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

DEVICE_FILE = "devices.yaml"

def normalize_mac(mac: str) -> str:
    """Convert MAC address to a consistent format without colons."""
    return mac.replace(":", "").lower()

@app.get("/ciscoise/mdminfo/")
def mdm_info(ise_api_version: Optional[str] = "2"):
    # Return static XML response as expected by Cisco ISE
    xml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<ise_api>
  <name>mdminfo</name>
  <api_version>3</api_version>
  <api_path>/ise/mdm/api</api_path>
  <redirect_url>https://wintermute-alpha.cisco.com/redirect</redirect_url>
  <query_max_size>3000</query_max_size>
  <messaging_support>false</messaging_support>
  <vendor>Mock_MDM</vendor>
  <product_name>Mock_MDM</product_name>
  <product_version>1.0.0</product_version>
</ise_api>
"""
    return Response(content=xml_response, media_type="application/xml")

def load_devices():
    if not os.path.exists(DEVICE_FILE):
        return {}

    with open(DEVICE_FILE, "r") as f:
        devices = yaml.safe_load(f)
        # Normalize MAC addresses in the loaded data
        return {normalize_mac(mac): attrs for mac, attrs in devices.items()}

@app.get("/ise/mdm/api/devices/")
def get_device_attributes(
    paging: Optional[str] = "0",
    querycriteria: Optional[str] = None,
    value: Optional[str] = None,
    filter: Optional[str] = "all"
):
    devices_data = load_devices()
    matched_devices = []

    # Normalize the MAC address in the query value if necessary
    if querycriteria == "macaddress" and value:
        value = normalize_mac(value)

    for mac, attrs in devices_data.items():
        if querycriteria == "macaddress":
            if not value or mac != value:
                continue
        elif querycriteria == "compliance":
            compliance_status = str(attrs.get("compliance", {}).get("status", "")).lower()
            if not value or compliance_status != value.lower():
                continue
        elif querycriteria == "username":
            if not value or str(attrs.get("username", "")).lower() != value.lower():
                continue
        # If no querycriteria provided, return all
        matched_devices.append((mac, attrs))

    # Build XML response
    device_xml = ""
    for mac, attrs in matched_devices:
        c = attrs.get("compliance", {})
        device_xml += f"""
<device>
    <macaddress>{mac}</macaddress>
    <attributes>
    <register_status>{str(attrs.get("register_status", "false")).lower()}</register_status>
    <compliance>
        <status>{str(c.get("status", "false")).lower()}</status>
        <failure_reason>{c.get("failure_reason", "")}</failure_reason>
        <remediation>{c.get("remediation", "")}</remediation>
    </compliance>
    <disk_encryption_on>{str(attrs.get("disk_encryption_on", "false")).lower()}</disk_encryption_on>
    <pin_lock_on>{str(attrs.get("pin_lock_on", "false")).lower()}</pin_lock_on>
    <jail_broken>{str(attrs.get("jail_broken", "false")).lower()}</jail_broken>
    <manufacturer>{attrs.get("manufacturer", "")}</manufacturer>
    <model>{attrs.get("model", "")}</model>
    <imei>{attrs.get("imei", "")}</imei>
    <meid>{attrs.get("meid", "")}</meid>
    <udid>{attrs.get("udid", "")}</udid>
    <serial_number>{attrs.get("serial_number", "")}</serial_number>
    <os_version>{attrs.get("os_version", "")}</os_version>
    <phone_number>{attrs.get("phone_number", "")}</phone_number>
    </attributes>
</device>
"""

    xml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<ise_api>
  <name>attributes</name>
  <api_version>2</api_version>
  <paging_info>0</paging_info>
  <deviceList>{device_xml}
  </deviceList>
</ise_api>
"""
    return Response(content=xml_response, media_type="application/xml")
