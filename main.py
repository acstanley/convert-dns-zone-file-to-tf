import os
import re
from collections import defaultdict

input_directory = r"C:\Users\LA\Downloads\idp\IDP"
output_directory = r"C:\Users\LA\Downloads\idp\out-tf"
resource_group_name = 'azurerm_resource_group.beauparc.name'

if not os.path.exists(output_directory):
    os.makedirs(output_directory)

for file in os.listdir(input_directory):
    if file.endswith('.txt'):
        domain = file.replace('.txt', '').replace('_', '.')
        input_file = os.path.join(input_directory, file)
        output_file = os.path.join(output_directory, f'dns-{domain}.tf')

        formatted_domain = domain.replace('.', '_')
        zone_resource_name = f"dns_zone__{formatted_domain}"

        with open(input_file, 'r') as in_file:
            content = in_file.readlines()

        record_dict = defaultdict(list)

        for line in content:
            line = line.strip()
            if not line.startswith(';'):
                record_match = re.match(r'(\S+)\s+\d+\s+IN\s+(\S+)\s+(.+)', line)
                if record_match:
                    full_name, rtype, value = record_match.groups()
                    if rtype not in ['NS', 'SOA']:
                        name = full_name.rstrip('.')
                        if name == domain:
                            name = "@"
                        else:
                            name = name.replace(f".{domain}", "")
                        formatted_name = f"{name.replace('.', '_')}_{formatted_domain}"
                        resource_name = f"dns_{rtype.lower()}__{formatted_name}"

                        if name == "@":
                            resource_name = f"dns_{rtype.lower()}__{formatted_domain}"

                        if rtype == 'TXT' and value.startswith('"') and value.endswith('"'):
                            value = value.strip('"')

                        if rtype in ['TXT', 'MX']:
                            record_dict[(rtype, resource_name, name)].append(value)
                        else:
                            record_dict[(rtype, resource_name, name, value)].append(value)

        with open(output_file, 'w') as out_file:
            zone_block = f"""resource "azurerm_dns_zone" "{zone_resource_name}" {{
  name                = "{domain}"
  resource_group_name = "{resource_group_name}"
}}
"""
            out_file.write(zone_block.strip() + '\n')

            for (rtype, resource_name, name, *value), _ in record_dict.items():
                if rtype == 'MX':
                    records_block = "\n".join([f"""
  record {{
    preference = {v.split()[0]}
    exchange   = "{v.split()[1]}"
  }}""" for v in record_dict[(rtype, resource_name, name)]])
                    resource_block = f"""
resource "azurerm_dns_mx_record" "{resource_name}" {{
  name                = "{name}"
  zone_name           = azurerm_dns_zone.{zone_resource_name}.name
  resource_group_name = "{resource_group_name}"
  ttl                 = 300
{records_block}
}}
"""
                elif rtype == 'TXT':
                    records_block = "\n".join([f"""
  record {{
    value = "{v}"
  }}""" for v in record_dict[(rtype, resource_name, name)]])
                    resource_block = f"""
resource "azurerm_dns_txt_record" "{resource_name}" {{
  name                = "{name}"
  zone_name           = azurerm_dns_zone.{zone_resource_name}.name
  resource_group_name = "{resource_group_name}"
  ttl                 = 300
{records_block}
}}
"""
                elif rtype == 'CNAME':
                    resource_block = f"""
resource "azurerm_dns_cname_record" "{resource_name}" {{
  name                = "{name}"
  zone_name           = azurerm_dns_zone.{zone_resource_name}.name
  resource_group_name = "{resource_group_name}"
  ttl                 = 300
  record              = "{value[0]}"
}}
"""
                else:
                    resource_block = f"""
resource "azurerm_dns_{rtype.lower()}_record" "{resource_name}" {{
  name                = "{name}"
  zone_name           = azurerm_dns_zone.{zone_resource_name}.name
  resource_group_name = "{resource_group_name}"
  ttl                 = 300
  records             = ["{value[0]}"]
}}
"""
                out_file.write(resource_block)