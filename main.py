import os
import re

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

        with open(input_file, 'r') as in_file:
            content = in_file.readlines()

        with open(output_file, 'w') as out_file:
            formatted_domain = domain.replace('.', '_')
            for line in content:
                line = line.strip()
                if not line.startswith(';'):
                    record_match = re.match(r'(\S+)\s+(\d+)\s+IN\s+(\S+)\s+(.+)', line)
                    if record_match:
                        full_name, ttl, rtype, value = record_match.groups()
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

                            if rtype == 'MX':
                                preference, exchange = value.split()
                                resource_block = f"""
resource "azurerm_dns_mx_record" "{resource_name}" {{
  name                = "{name}"
  zone_name           = azurerm_dns_zone.dns_zone__{formatted_domain}.name
  resource_group_name = "{resource_group_name}"
  ttl                 = {ttl}

  record {{
    preference = {preference}
    exchange   = "{exchange}"
  }}
}}
"""
                            else:
                                resource_block = f"""
resource "azurerm_dns_{rtype.lower()}_record" "{resource_name}" {{
  name                = "{name}"
  zone_name           = azurerm_dns_zone.dns_zone__{formatted_domain}.name
  resource_group_name = "{resource_group_name}"
  ttl                 = {ttl}
  records             = ["{value}"]
}}
"""
                            out_file.write(resource_block)