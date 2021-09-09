'''
To run the job:

$ pyats run job C3PL_job.py --testbed-file ../testbeds/testbed_sample.yml

'''

import os
from genie.testbed import load

def main(runtime):

    # ----------------
    # Load the testbed
    # ----------------
    if not runtime.testbed:
        # If no testbed is provided, load the default one.
        # Load default location of Testbed
        testbedfile = os.path.join('../testbeds/testbed_sample.yml')
        testbed = load(testbedfile)
    else:
        # Use the one provided
        testbed = runtime.testbed

    # Find the location of the script in relation to the job file
    testscript = os.path.join(os.path.dirname(__file__), 'C3PL.py')

    # run script
    runtime.tasks.run(testscript=testscript, testbed=testbed)