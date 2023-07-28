'''Looks for ASG optimisations'''
import json, sys

def get_rule_string_list(rules):
  rule_list = []
  for rule in rules:
    rule_list.append(f"{rule['destination']}_{rule['protocol']}_{rule['ports']}")
  return rule_list

def main(file_name):
  '''Main function'''
  with open(file_name, encoding="utf-8") as open_file:
    asg_data = json.load(open_file)

  covered_by_defaults, org_data = parse_asgs(asg_data)

  org_common_saving = look_for_common_org_rules(org_data)

  rules_processed = 0
  for asg in asg_data:
    rules_processed += len(asg["rules"])

  print(f"Processed {len(asg_data)} ASGs")
  print(f"Processed {rules_processed} rules")
  print(f"Number of rules covered by default ASG: {len(covered_by_defaults)}")
  print(f"Number of rules that could be covered by common org ASG: {org_common_saving}")

def look_for_common_org_rules(org_data):
  org_common_saving = 0

  for org_name, org_details in org_data.items():
    if org_details["space_count"] < 2 or org_details["asgs"] < 2:
      continue
    for rule_details, rule_spaces in org_details["rules"].items():
      if len(rule_spaces) == org_details["space_count"]:
        org_common_saving += org_details["space_count"] - 1

  return org_common_saving

def iterate_dict_value(lookup_dict, key):
  if not key in lookup_dict:
    lookup_dict[key] = 1
    return
  lookup_dict[key] = lookup_dict[key] + 1

def extract_org_data(asg_data):
  '''Returns a dict, with org name as key and space_count/spaces as subkeys '''
  org_data = {}
  for asg in asg_data:
    added_orgs = set()
    for org_space_joined in asg["spaces"]:
      org_name, space_name = org_space_joined.split("_")[0], org_space_joined.split("_")[1]
      if not org_name in org_data:
        org_data[org_name] = {
          "space_count": 1,
          "spaces": {space_name},
          "rules": {},
          "asgs": 0
        }
      elif not space_name in org_data[org_name]["spaces"]:
          org_data[org_name]["space_count"] = org_data[org_name]["space_count"] + 1
          org_data[org_name]["spaces"].add(space_name)
      
      added_orgs.add(org_name)
  
    for added_org_name in added_orgs:
      org_data[added_org_name]["asgs"] += 1
  return org_data

def assign_rule_org_mapping(org_data, asg, rule_string):
  
  for org_space_name  in asg["spaces"]:
    org_name, space_name = org_space_name.split("_")[0], org_space_name.split("_")[1]

    if rule_string not in  org_data[org_name]["rules"]:
      org_data[org_name]["rules"][rule_string] = {space_name}
    else:
      org_data[org_name]["rules"][rule_string].add(space_name)


def parse_asgs(asg_data):
  # Tests
  # [x] destination is covered by the default ASG
  # [x] destination appears all spaces in the same org
  # [ ] destination is mapped to same space via another ASG
  # [ ] destination appears in a large number of orgs
  # [ ] check for duplicate rules inside an ASG
  # [ ] check for rules that could be combined due to a shared target and protocol
  # [ ] asg is applied to to many spaces for NSX-T

  default_rules = get_rule_string_list(asg_data[0]["rules"])
  org_data = extract_org_data(asg_data)
  covered_by_defaults = []

  for asg in asg_data:
    # Skip default ASG
    if asg["asg_name"] == "default_security_group" or "" not in asg["asg_name"]:
      continue

    for rule in asg["rules"]:
      rule_string = f"{rule['destination']}_{rule['protocol']}_{rule['ports']}"

      if rule_string in default_rules:
        covered_by_defaults.append(rule.update({"org_space": asg["spaces"], "asg_name": asg["asg_name"]}))

      assign_rule_org_mapping(org_data, asg, rule_string)
  return covered_by_defaults, org_data

if __name__ == "__main__":
  # TODO test for user input!!!
  FILE_NAME = sys.argv[1]
  main(FILE_NAME)
