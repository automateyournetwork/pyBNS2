# ----------------
# Copyright
# ----------------
# Written by John Capobianco, March 2021, Justin Thériault, August 2021
# Copyright (c) 2021 John Capobianco

# ----------------
# Python
# ----------------
import os
import sys
import yaml
import time
import json
import shutil
import logging
from pyats import aetest
from pyats import topology
from pyats.log.utils import banner
from genie.utils.diff import Diff
from jinja2 import Environment, FileSystemLoader
from general_functionalities import ParseConfigFunction, ParseShowCommandFunction
from datetime import datetime
from contextlib import redirect_stdout

log = logging.getLogger(__name__)
template_dir = 'templates/'
env = Environment(loader=FileSystemLoader(template_dir))
timestr = datetime.now().strftime("%Y%m%d_%H%M%S")

# ----------------
# AE Test Setup
# ----------------
class common_setup(aetest.CommonSetup):
    """Common Setup section"""
    @aetest.subsection
    def connect_to_devices(self, testbed):
        """Connect to all the devices"""
        testbed.connect()

# ----------------
# Test Case #1
# ----------------
class Collect_Information(aetest.Testcase):
    """Parse all the commands"""

    @aetest.test
    def parse(self, testbed, section, steps):
        """ Testcase Setup section """
        # ---------------------------------------
        # Loop over devices
        # ---------------------------------------
        for device in testbed:
       
            # ---------------------------------------
            # 0. Take Backup 
            # --------------------------------------- 
            backup_config_filename = "%s_Backup_%s.cfg" % (device.alias,timestr)
            
            with open("backup_configs/%s" % backup_config_filename, "w") as fid:
                fid.write(device.execute("show run"))
                fid.close()


            # ---------------------------------------
            # 1. Pre-Change State 
            # ---------------------------------------  

            # ---------------------------------------
            # Get running config -> Genie learn('config').info for pre-change state 
            # ---------------------------------------
            self.learned_config = ParseConfigFunction.parse_learn(steps, device, "config")
            pre_learned_config = self.learned_config

            #----------------------------------------
            # Save Running Config into JSON Pre-Change File
            #----------------------------------------
            with steps.start('Store Original Golden Image',continue_=True) as step:
                
                pre_config_filename = "%s_Pre_Running_Config_%s.json" % (device.alias,timestr)
                # Write Original Learned Config as JSON
                if hasattr(self, 'learned_config'):
                    with open("pre_configs/%s" % pre_config_filename, "w") as fid:
                        json.dump(self.learned_config, fid, indent=4, sort_keys=True)
                        fid.close()

            # ---------------------------------------
            # Get pre-change state of MAC address table
            # ---------------------------------------
            self.parsed_mac_table = ParseShowCommandFunction.parse_show_command(steps, device, "show mac address-table")
            pre_parsed_mac_table = self.parsed_mac_table


            #----------------------------------------
            # Save MAC Table into JSON Pre-Change File
            #----------------------------------------
            with steps.start('Store Pre-state MAC Table',continue_=True) as step:
                
                pre_mac_table_filename = "%s_Pre_MAC_Table_%s.json" % (device.alias,timestr)
                # Write Original Learned Config as JSON
                with open("pre_configs/%s" % pre_mac_table_filename, "w") as fid:
                    json.dump(self.parsed_mac_table, fid, indent=4, sort_keys=True)
                    fid.close()

            # ---------------------------------------
            # Get pre-change state of Dot1x interfaces 
            # ---------------------------------------
            self.parsed_dot1x = ParseShowCommandFunction.parse_show_command(steps, device, "show dot1x all details")
            pre_parsed_dot1x = self.parsed_dot1x

            #----------------------------------------
            # Save dot1x ports to JSON Pre-Change File
            #----------------------------------------
            with steps.start('Store Pre State Dot1x Interfaces',continue_=True) as step:
                
                pre_dot1x_filename = "%s_Pre_Dot1x_%s.json" % (device.alias,timestr)
                # Write Original Learned Config as JSON
                with open("pre_configs/%s" % pre_dot1x_filename, "w") as fid:
                    json.dump(self.parsed_dot1x, fid, indent=4, sort_keys=True)
                    fid.close()

            # ---------------------------------------
            # Get pre-change state of Authentication sessions 
            # ---------------------------------------
            self.parsed_auth_sessions = ParseShowCommandFunction.parse_show_command(steps, device, "show authentication sessions")
            pre_parsed_auth_sessions = self.parsed_auth_sessions

            #----------------------------------------
            # Save Authentication sessions to JSON Pre-Change File
            #----------------------------------------
            with steps.start('Store Pre State Authentication Sessions',continue_=True) as step:
                
                pre_auth_sessions_filename = "%s_Pre_Authentication_Sessions_%s.json" % (device.alias,timestr)
                # Write Original Learned Config as JSON
                with open("pre_configs/%s" % pre_auth_sessions_filename, "w") as fid:
                    json.dump(self.parsed_auth_sessions, fid, indent=4, sort_keys=True)
                    fid.close()

            # ---------------------------------------
            # Genie parse 'show int status' to capture all interfaces on switch
            # ---------------------------------------
            self.parsed_int_status = ParseShowCommandFunction.parse_show_command(steps, device, "show interfaces status")
            pre_parsed_int_status = self.parsed_int_status

            #----------------------------------------
            # Save all interfaces to JSON Pre-Change File
            #----------------------------------------
            with steps.start('Store Pre State Interface Status',continue_=True) as step:
                
                original_config_filename = "%s_Pre_Interfaces_Status_%s.json" % (device.alias,timestr)
                # Write Original Learned Config as JSON
                with open("pre_configs/%s" % original_config_filename, "w") as fid:
                    json.dump(self.parsed_int_status, fid, indent=4, sort_keys=True)
                    fid.close()
            #----------------------------------------
            # Keep only Access interfaces
            #----------------------------------------
            access_interface_array = []
            for interface,values in pre_parsed_int_status['interfaces'].items():
                if values['vlan'] != "trunk" and values['vlan'] != "routed" and interface != "Ap1/0/1" and "/1/" not in interface:
                    access_interface_array.append(interface)
                    
            print(access_interface_array) 

            # ---------------------------------------
            # 2. Wipe Dot1x configs from all ports 
            # ---------------------------------------  
            
            #---------------------------------------
            # Create Intent from legacy_dot1x_removal.j2 Template and Data Models
            # ---------------------------------------
            with steps.start('Wipe Legacy Dot1x Configs from all ports',continue_=True) as step:
                legacy_removal_template = env.get_template('legacy_dot1x_removal.j2')
                legacy_removal = legacy_removal_template.render(interface=access_interface_array)           
                with open("templates/%s_legacy_removal.txt" % timestr, "w") as fid:
                    fid.write(legacy_removal)
                    fid.close()
          
            #----------------------------------------
            # Write Pre-Change File
            #---------------------------------------
 
            device.configure(legacy_removal) 
 
            # ---------------------------------------
            # 3. Convert Dot1x to new-style 
            # ---------------------------------------  
           
            device.execute("authentication display new-style")

            # ---------------------------------------
            # 4. Remove all default policy-maps and service templates 
            # --------------------------------------- 
            
            junk_interface_removal_template = env.get_template('junk_interface_removal_template.j2')
            junk_interface_removal = junk_interface_removal_template.render(interface=access_interface_array)
            
            with steps.start("Remove applied default policy per interface", continue_=True) as step:
                try:
                    device.configure(junk_interface_removal)
                except Exception as e:
                    step.failed('Could not remove applied policy correctly\n{e}'.format(e=e))             
        
            junk_removal_template = env.get_template('junk_removal_template.j2')
            junk_removal = junk_removal_template.render(interface=access_interface_array)

            with steps.start("Remove global default policies and templates", continue_=True) as step:
                try:
                    device.configure(junk_removal)
                except Exception as e:
                    step.failed('Could not remove global configs correctly\n{e}'.format(e=e))

            # ---------------------------------------
            # 4. Capture Data VLAN ID
            # ---------------------------------------
            vlanlist = device.learn("vlan").info
            for vlan in vlanlist['vlans']:
                if vlanlist['vlans'][vlan]['name'] == "data_vlan":
                    data_vlan = vlanlist['vlans'][vlan]['vlan_id']

            new_global_config_template = env.get_template('C3PL_new_global_configs.j2')
            new_global_config = new_global_config_template.render(vlan=data_vlan)

            device.configure(new_global_config)
 
            # ---------------------------------------
            # 5. Add per-interface new config 
            # ---------------------------------------

            #Ask for enforcement or monitor before applying config to interfaces?
            
            print(pre_parsed_dot1x)

            if "interfaces" in pre_parsed_dot1x:
                with steps.start('Applying new interface configs',continue_=True) as step:
                    new_int_template = env.get_template('C3PL_new_int_config_enforcement.j2')
                    new_int_config = new_int_template.render(interface=pre_parsed_dot1x['interfaces']) 

                    device.configure(new_int_config)

            # ---------------------------------------
            # Write mem once complete
            # ---------------------------------------
            device.execute("wr mem")

            # ---------------------------------------
            # Re-capture state - Running config
            # ---------------------------------------
            self.learned_config = ParseConfigFunction.parse_learn(steps, device, "config")
            post_learned_config = self.learned_config
#
            # ---------------------------------------
            # Write post-change state - Running Config
            # ---------------------------------------
            with steps.start('Store Post Running Config',continue_=True) as step:
                
                new_config_filename = "%s_Post_Running_Config_%s.json" % (device.alias,timestr)
#
            # Write New Learned Config as JSON
                if hasattr(self, 'learned_config'):
                    with open("post_configs/%s" % new_config_filename, "w") as fid:
                        json.dump(self.learned_config, fid, indent=4, sort_keys=True)
                        fid.close()
#
            # ---------------------------------------
            # Show the differential - Running Config
            # ---------------------------------------
            with steps.start('Show Running Config Differential',continue_=True) as step:
                config_diff = Diff(pre_learned_config, post_learned_config)
                config_diff.findDiff()
                
                if config_diff.diffs:
                    print(config_diff)
                
                    with open('changelog/%s_C3PL_Conversion_Running_Config.txt_%s' % (device.alias,timestr), 'w') as f:
                        with redirect_stdout(f):
                            print(config_diff)
                            f.close()
    #
                else:
                    
                    with open('changelog/%s_C3PL_Conversion_Running_Config.txt_%s' % (device.alias,timestr), 'w') as f:
                        f.write("NO CHANGES")
                        f.close()
             
            # ---------------------------------------
            # Re-capture state - MAC Table 
            # ---------------------------------------
            self.parsed_mac_table = ParseShowCommandFunction.parse_show_command(steps, device, "show mac address-table")
            post_parsed_mac_table = self.parsed_mac_table 

            # ---------------------------------------
            # Write post-change state - MAC Table
            # ---------------------------------------
            with steps.start('Store Post MAC Table',continue_=True) as step:
                
                new_config_filename = "%s_Post_MAC_Table_%s.json" % (device.alias,timestr)
#
            # Write New Learned Config as JSON
                with open("post_configs/%s" % new_config_filename, "w") as fid:
                    json.dump(self.parsed_mac_table, fid, indent=4, sort_keys=True)
                    fid.close()
#
            # ---------------------------------------
            # Show the differential - MAC TAble
            # ---------------------------------------
            with steps.start('Show MAC Table Differential',continue_=True) as step:
                config_diff = Diff(pre_parsed_mac_table, post_parsed_mac_table)
                config_diff.findDiff()
                
                if config_diff.diffs:
                    print(config_diff)
                
                    with open('changelog/%s_C3PL_Conversion_MAC_Table.txt_%s' % (device.alias,timestr), 'w') as f:
                        with redirect_stdout(f):
                            print(config_diff)
                            f.close()
    #
                else:
                    
                    with open('changelog/%s_C3PL_Conversion_MAC_Table.txt_%s' % (device.alias,timestr), 'w') as f:
                        f.write("NO CHANGES")
                        f.close()

            # ---------------------------------------
            # Re-capture state - Dot1x 
            # ---------------------------------------
            self.parsed_dot1x = ParseShowCommandFunction.parse_show_command(steps, device, "show mac address-table")
            post_parsed_dot1x = self.parsed_dot1x 


            # ---------------------------------------
            # Write post-change state - Dot1x 
            # ---------------------------------------
            with steps.start('Store Post Dot1x',continue_=True) as step:
                
                new_config_filename = "%s_Post_Dot1x_%s.json" % (device.alias,timestr)
#
            # Write New Learned Config as JSON
                with open("post_configs/%s" % new_config_filename, "w") as fid:
                    json.dump(self.parsed_dot1x, fid, indent=4, sort_keys=True)
                    fid.close()

#
            # ---------------------------------------
            # Show the differential - Dot1x
            # ---------------------------------------
            with steps.start('Show Dot1x Differential',continue_=True) as step:
                config_diff = Diff(pre_parsed_dot1x, post_parsed_dot1x)
                config_diff.findDiff()
                
                if config_diff.diffs:
                    print(config_diff)
                
                    with open('changelog/%s_C3PL_Conversion_Dot1x.txt_%s' % (device.alias,timestr), 'w') as f:
                        with redirect_stdout(f):
                            print(config_diff)
                            f.close()
    #
                else:
                    
                    with open('changelog/%s_C3PL_Conversion_Dot1x.txt_%s' % (device.alias,timestr), 'w') as f:
                        f.write("NO CHANGES")
                        f.close()

            # ---------------------------------------
            # Re-capture state - Authentication Sessions 
            # ---------------------------------------
            self.parsed_auth_sessions = ParseShowCommandFunction.parse_show_command(steps, device, "show authentication sessions")
            post_parsed_auth_sessions = self.parsed_auth_sessions 

            # ---------------------------------------
            # Write post-change state - Authentication Sessions 
            # ---------------------------------------
            with steps.start('Store Post Authentication Sessions',continue_=True) as step:
                
                new_config_filename = "%s_Post_Authentication_Sessions_%s.json" % (device.alias,timestr)
#
            # Write New Learned Config as JSON
                with open("post_configs/%s" % new_config_filename, "w") as fid:
                    json.dump(self.parsed_auth_sessions, fid, indent=4, sort_keys=True)
                    fid.close()
#
            # ---------------------------------------
            # Show the differential - Authentication Sessions
            # ---------------------------------------
            with steps.start('Show Authentication Sessions Differential',continue_=True) as step:
                config_diff = Diff(pre_parsed_auth_sessions, post_parsed_auth_sessions)
                config_diff.findDiff()
                
                if config_diff.diffs:
                    print(config_diff)
                
                    with open('changelog/%s_C3PL_Conversion_Authentication_Sessions.txt_%s' % (device.alias,timestr), 'w') as f:
                        with redirect_stdout(f):
                            print(config_diff)
                            f.close()
    #
                else:
                    
                    with open('changelog/%s_C3PL_Conversion_Authentication_Sessions.txt_%s' % (device.alias,timestr), 'w') as f:
                        f.write("NO CHANGES")
                        f.close()

            # ---------------------------------------
            # Re-capture state - Interfaces 
            # ---------------------------------------
            self.parsed_int_status = ParseShowCommandFunction.parse_show_command(steps, device, "show interfaces status")
            post_parsed_int_status = self.parsed_int_status 


            # ---------------------------------------
            # Write post-change state - Interfaces 
            # ---------------------------------------
            with steps.start('Store Post Interfaces',continue_=True) as step:
                
                new_config_filename = "%s_Post_Interfaces_%s.json" % (device.alias,timestr)
#
            # Write New Learned Config as JSON
                with open("post_configs/%s" % new_config_filename, "w") as fid:
                    json.dump(self.parsed_int_status, fid, indent=4, sort_keys=True)
                    fid.close()

#
            # ---------------------------------------
            # Show the differential - Interfaces
            # ---------------------------------------
            with steps.start('Show Interfaces Differential',continue_=True) as step:
                config_diff = Diff(pre_parsed_int_status, post_parsed_int_status)
                config_diff.findDiff()
                
                if config_diff.diffs:
                    print(config_diff)
                
                    with open('changelog/%s_C3PL_Conversion_Interfaces.txt_%s' % (device.alias,timestr), 'w') as f:
                        with redirect_stdout(f):
                            print(config_diff)
                            f.close()
    #
                else:
                    
                    with open('changelog/%s_C3PL_Conversion_Interfaces.txt_%s' % (device.alias,timestr), 'w') as f:
                        f.write("NO CHANGES")
                        f.close()