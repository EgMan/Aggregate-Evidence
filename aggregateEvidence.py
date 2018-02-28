'''
Todo:
add argument to force superset
add argumentparser support
'''
import xml.etree.ElementTree as ET
import sys
import os
import re

def main():
    directory = gather_params()
    evidences, evidence_superset = gather_evidence(directory)
    aggregate(evidences, evidence_superset)
    post_process(evidence_superset)
    dump_to_file(evidence_superset, directory, "_aggregated_{0}".format(evidence_superset.file_name))

def gather_params():
    if len(sys.argv) > 1:
        return sys.argv[1]
    return "./"

def gather_evidence(dir):
    evidences = []
    evidence_superset = None
    print("\nLooking for evidence in {0} :".format(dir))
    for file in os.listdir(dir):
        if file.endswith(".xml"):
            evidence = Evidence(dir, file)
            if evidence.testcase_num != 0:
                evidences.append(evidence)
                cprint("\t{0} {1}({2} completed tests, {3} failures, {4} errors)".format(file, bcolors.OKBLUE, evidence.testcase_num, evidence.failure_num, evidence.error_num), bcolors.ENDC)

                #This is the logic for finding the superset to use
                #Assuming there are no duplicates, if there exists a test case superset, it must be the suite with the most test cases
                #If suites are tied for the most test cases, the suite with the least failures is used
                if evidence_superset == None or evidence.testcase_num > evidence_superset.testcase_num:
                    evidence_superset = evidence
                elif evidence.testcase_num == evidence_superset.testcase_num and evidence.failure_num < evidence_superset.failure_num:
                    evidence_superset = evidence
    if evidence_superset == None:
        cprint("No evidence was found in this directory", bcolors.FAIL)
        quit()

    cprint("Using {0} as a superset".format(evidence_superset.file_name), bcolors.OKGREEN)
    evidences.remove(evidence_superset)
    return (evidences, evidence_superset)

def aggregate(evidences, evidenceTo):
    print("\nStitching in evidence")
    ignoredTestIndicator = False
    stitchedTestIndicator = False
    for evidenceFrom in evidences:
        for testcaseFrom in evidenceFrom.elem_dict:
            testCaseFromElem = evidenceFrom.elem_dict[testcaseFrom];
            for failureType in ['failure', 'error']:
                if testCaseFromElem.find(failureType) == None and testCaseFromElem.get('incomplete') != "true":
                    if testcaseFrom in evidenceTo.elem_dict:
                        testcaseTo = evidenceTo.elem_dict[testcaseFrom]
                        failureToRemove = testcaseTo.find(failureType)
                        if failureToRemove != None:
                            testcaseTo.remove(failureToRemove)
                            stitchedTestIndicator = True
                            cprint("Removed {0} {1} from superset because it passes in {2}".format(failureType, testcaseTo.get('name'), evidenceFrom.file_name), bcolors.OKGREEN)
                    elif not testcaseFrom.startswith('Unrooted Tests'):
                        ignoredTestIndicator = True
                        cprint("WARNING: ignoring testcase {0} not found in superset".format(testcaseFrom), bcolors.FAIL)
    if stitchedTestIndicator == False:
        cprint("Superset {0} is the best run so far and none of its failures have ever passed.  Aggregated evidence will still be written, but it's just a copy of the superset.".format(evidenceTo.file_name), bcolors.WARNING)
    if ignoredTestIndicator == True:
        cprint("Some tests were not found in superset.  Please make sure there is at least one evidence file which contains all of the test cases. This could also be caused by evidence which isn't all from the same test suite.", bcolors.FAIL)

def post_process(evidence):
    failing_tests = []
    testrun = None
    fail_num = 0
    err_num = 0

    print("\nWrapping things up")

    for testcase in evidence.elem_dict:
        if evidence.elem_dict[testcase].find('failure') != None:
            fail_num = fail_num + 1
            failing_tests.append(testcase)
        if evidence.elem_dict[testcase].find('error') != None:
            err_num = err_num + 1
            failing_tests.append(testcase)
    failing_tests = sorted(failing_tests)

    #Update failures and errors fields in testrun
    if evidence.root_elem.tag == 'testrun':
        testrun = evidence.root_elem
    else:
        testrun = evidence.root_elem.find('testrun')
    if testrun != None:
        testrun.set('failures', str(fail_num))
        testrun.set('errors', str(err_num))
    else:
        cprint("WARNING: your superset was not run under the context of a 'testrun' element", bcolors.WARNING)

    if len(failing_tests) != 0:
        cprint("Tests which still fail across all evidence parsed:", bcolors.WARNING)
        for test in failing_tests:
            cprint("\t{0}".format(test), bcolors.WARNING)
    else:
        cprint("All tests have passed at least once across all of the evidences", bcolors.OKGREEN)

def dump_to_file(evidence, file_path, file_name):
    location = os.path.join(file_path, "aggregated")
    location_andfile = os.path.join(location, file_name)
    if not os.path.exists(location):
        try:
            os.makedirs(location)
        except OSError as e: # Guard against race condition
            cprint("WARNING: Could not make aggregated subfolder, will write data to {0} instead\n{1}".format(file_path, e), bcolors.WARNING)
            location_andfile = os.path.join(file_path, file_name)
    with open(location_andfile, "w") as evidence_file:
        #This substitution is done because ElementTreeAPI's empty xml element syntax looks like
        #<testcase></testcase>, but we want it to look like <testcase/>
        output_text = re.sub(r'(<testcase[^>]*)>\s*</testcase>', r'\1 />', ET.tostring(evidence.root_elem).decode('utf-8'))
        evidence_file.write(output_text)
        print("Evidence written to {0}".format(location_andfile))

class Evidence:
    def __init__(self, root_path, file_name):
        self.testcase_num = 0
        self.failure_num = 0
        self.error_num = 0
        self.file_name = file_name
        self.file_path = os.path.join(root_path, file_name)
        self.root_elem = ET.parse(self.file_path).getroot()
        self.elem_dict = self.__index_evidence()

    def __index_evidence(self):
        evidence_dict = {}
        return self.__index_evidence_helper(self.root_elem, evidence_dict, None)

    def __index_evidence_helper(self, node, evidence_dict, index_prefix):
        for child in node:
            #Assure that the inexes of testcases which are children of a testsuite
            #are prefixed with that suite's name
            if node.tag != 'testsuite':
                self.__index_evidence_helper(child, evidence_dict, index_prefix)
            elif node.get('name').lower() != "unrooted tests":
                self.__index_evidence_helper(child, evidence_dict, node.get('name'))

        if node.tag == 'testcase' and node.get('incomplete') != "true":
            #setup index for easy access
            if index_prefix == None:
                index = node.get('name')
            else:
                index = "{0}-{1}".format(index_prefix, node.get('name'))
            evidence_dict[index] = node

            self.testcase_num = self.testcase_num + 1
            if node.find('failure') != None:
                self.failure_num = self.failure_num + 1
            if node.find('error') != None:
                self.error_num = self.error_num + 1
        return evidence_dict

class bcolors:
        HEADER = '\033[95m'
        OKBLUE = '\033[94m'
        OKGREEN = '\033[92m'
        WARNING = '\033[93m'
        FAIL = '\033[91m'
        ENDC = '\033[0m'
        BOLD = '\033[1m'
        UNDERLINE = '\033[4m'
def cprint(message, color):
    print("{0}{1}{2}".format(color,message,bcolors.ENDC))

if __name__ == '__main__':
    main()
