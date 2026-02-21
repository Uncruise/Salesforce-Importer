# -*- coding: utf-8 -*-
"""Nonprofit Salesforce © 2022 by Adventure Ready Consulting is licensed under CC BY 4.0"""

"""import Module for Excel to Salesforce"""

"""Helpful Link: https://pbpython.com/windows-com.html"""

try:
    from win32api import STD_INPUT_HANDLE
    from win32console import GetStdHandle, ENABLE_PROCESSED_INPUT
except ImportError as ex:
    print(str(ex))

class KeyboardHook():
    """Keyboard Hook Class"""

    def __enter__(self):
        self.readHandle = GetStdHandle(STD_INPUT_HANDLE)
        self.readHandle.SetConsoleMode(ENABLE_PROCESSED_INPUT)

        self.input_lenth = len(self.readHandle.PeekConsoleInput(10000))

        return self

    def __exit__(self, type, value, traceback):
        pass

    def reset(self):
        self.input_lenth = len(self.readHandle.PeekConsoleInput(10000))

        return True

    def key_pressed(self):
        """poll method to check for keyboard input"""

        events_peek = self.readHandle.PeekConsoleInput(10000)

        #Events come in pairs of KEY_DOWN, KEY_UP so wait for at least 2 events
        if len(events_peek) >= (self.input_lenth + 2):
            self.input_lenth = len(events_peek)
            return True

        return False

def main():
    """Main entry point"""

    import sys
    import os
    from os import listdir, makedirs
    from os.path import exists, join

    #
    # Required Parameters
    #

    salesforce_type = str(sys.argv[1])
    client_type = str(sys.argv[2])
    client_subtype = str(sys.argv[3])
    client_emaillist = str(sys.argv[4])

    if len(sys.argv) < 5:
        print("Calling error - missing required inputs.  Expecting " +
               "salesforce_type client_type client_subtype client_emaillist\n")
        return

    print("\nIncoming required parameters: " +
           "salesforce_type: {} client_type: {} client_subtype: {} client_emaillist: {} sys.argv {}\n"
           .format(salesforce_type, client_type, client_subtype, client_emaillist, sys.argv))

    print("\n\nWhen import complete a status email with be sent to {}\n\n"
           .format(client_emaillist))

    print("\n\nThis process can take up to 30 minutes to complete...")

    #
    # Optional Parameters
    #

    wait_time = 300
    if '-waittime' in sys.argv:
        wait_time = int(sys.argv[sys.argv.index('-waittime') + 1])

    norefresh = False
    if '-norefresh' in sys.argv:
        norefresh = True

    noupdate = False
    if '-noupdate' in sys.argv:
        noupdate = True

    enabledelete = False
    if '-enabledelete' in sys.argv:
        enabledelete = True

    noexportpostgres = False
    if '-noexportpostgres' in sys.argv:
        noexportpostgres = True

    noexportodbc = False
    if '-noexportodbc' in sys.argv:
        noexportodbc = True

    noexportsf = False
    if '-noexportsf' in sys.argv:
        noexportsf = True

    global emailattachments
    emailattachments = False
    if '-emailattachments' in sys.argv:
        emailattachments = True

    interactivemode = False
    if '-interactivemode' in sys.argv:
        interactivemode = True

    displayalerts = False
    if '-displayalerts' in sys.argv:
        displayalerts = True

    skipexcelrefresh = False
    if '-skipexcelrefresh' in sys.argv:
        skipexcelrefresh = True

    insert_attempts = 10
    if '-insertattempts' in sys.argv:
        insert_attempts = int(sys.argv[sys.argv.index('-insertattempts') + 1])

    location_local = True
    if 'Cloud' in sys.argv:
        location_local = False

    updaterequired = False
    if 'UpdateRequired' in client_subtype:
        updaterequired = True

    if 'Manifest' in client_subtype:
        wait_time = 30

    importer_root = ("C:\\repo\\Salesforce-Importer-Private\\Clients\\" + client_type +
                     "\\Salesforce-Importer")
    if '-rootdir' in sys.argv:
        importer_root = sys.argv[sys.argv.index('-rootdir') + 1]

    # Setup Logging to File
    sys_stdout_previous_state = sys.stdout
    if not interactivemode:
        sys.stdout = open(join(importer_root, '..\\importer.log'), 'w')
    print('Importer Startup')

    importer_directory = join(importer_root, "Clients\\" + client_type)
    print("Setting Importer Directory: ", importer_directory)

    # Global to monitor if should exit all processing
    global stop_processing
    stop_processing = False

    #Cloud location setup status results
    if not location_local:

        f = open(join(importer_directory, "ImportInstance_Status.txt"), "w")
        f.write("Complete")
        f.close()

    #Clear out log directory
    importer_log_directory = join(importer_root, "..\\Status\\")
    print("Check Status Directory: ", importer_log_directory)
    if not exists(importer_log_directory):
        makedirs(importer_log_directory)

    importer_log_directory = join(importer_log_directory, client_subtype)
    print("Check Status Client Directory: ", importer_log_directory)
    if not exists(importer_log_directory):
        makedirs(importer_log_directory)

    print("Clearing out the Importer Log Directory: ", importer_log_directory)
    for file_name_only in listdir(importer_log_directory):
        file_name_full = join(importer_log_directory, file_name_only)
        if os.path.isfile(file_name_full):
            os.remove(file_name_full)

    # Export External Data
    status_export = ""

    if not noexportpostgres:
        print("\n\nExporter - Export External Data from Postgres\n\n")
        status_export = export_postgres(importer_directory,
                                    salesforce_type,
                                    client_subtype,
                                    client_emaillist,
                                    interactivemode,
                                    displayalerts)

    if not noexportodbc:
        print("\n\nExporter - Export External Data ODBC\n\n")
        status_export = export_odbc(importer_directory,
                                    salesforce_type,
                                    client_subtype,
                                    interactivemode,
                                    displayalerts)

    # Check filename for operation
    insertOnly = False
    if "insert" in client_subtype.lower():
        insertOnly = True

    updateOnly = False
    if "update" in client_subtype.lower() or "upsert" in client_subtype.lower():
        updateOnly = True

    reportOnly = False
    if "report" in client_subtype.lower() and not updateOnly and not insertOnly:
        reportOnly = True

    print("norefresh: ", str(norefresh))
    print("noupdate: ", str(noupdate))
    print("insertOnly: ", str(insertOnly))
    print("updateOnly: ", str(updateOnly))
    print("reportOnly: ", str(reportOnly))

    # Insert Data
    status_import = ""
    if not norefresh and not updateOnly and not reportOnly and "Invalid Return Code" not in status_export:
        for insert_run in range(0, insert_attempts):

            print("\n\nImporter - Insert Data Process (run: %d)\n\n" % (insert_run))

            status_import = process_data(importer_directory, salesforce_type, client_type,
                                         client_subtype, 'Insert', wait_time,
                                         noexportsf,
                                         interactivemode,
                                         displayalerts,
                                         skipexcelrefresh,
                                         location_local,
                                         updaterequired)

            if stop_processing:
                return

            # Insert files are empty so continue to update process
            if "import_dataloader (returncode)" not in status_import:
                break

    # Update Data
    if not noupdate and not insertOnly and not reportOnly and not contains_error(status_import):
        print("\n\nImporter - Update Data Process\n\n")

        status_import = process_data(importer_directory, salesforce_type, client_type,
                                    client_subtype, 'Upsert', wait_time,
                                    noexportsf,
                                    interactivemode,
                                    displayalerts,
                                    skipexcelrefresh,
                                    location_local,
                                    updaterequired)

        status_import += process_data(importer_directory, salesforce_type, client_type,
                                     client_subtype, 'Update', wait_time,
                                     noexportsf, interactivemode, displayalerts, skipexcelrefresh, location_local,
                                     updaterequired)

    # Report Data
    if reportOnly and not insertOnly and not updateOnly:
        print("\n\nImporter - Report Data Process\n\n")

        status_import += process_data(importer_directory, salesforce_type, client_type,
                                     client_subtype, 'Report', wait_time,
                                     noexportsf, interactivemode, displayalerts, skipexcelrefresh, location_local,
                                     updaterequired)

    if stop_processing:
        return

    # Delete Data
    if enabledelete and not insertOnly and not updateOnly and not contains_error(status_import):
        print("\n\nImporter - Delete Data Process\n\n")
        status_import = process_data(importer_directory, salesforce_type, client_type,
                                     client_subtype, 'Delete', wait_time,
                                     noexportsf, interactivemode, displayalerts, skipexcelrefresh, location_local,
                                     updaterequired)

    if stop_processing:
        return

    # Restore stdout
    sys.stdout = sys_stdout_previous_state

    output_log = ""
    if not interactivemode:
        with open(join(importer_root, "..\\importer.log"), 'r') as exportlog:
            output_log = exportlog.read()

    file_path = importer_directory + "\\Status"
    import datetime
    date_tag = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    with open(join(file_path, "Salesforce-Importer-Log-{}.txt".format(date_tag)),
              "w") as text_file:
        text_file.write(output_log)

    #Write log to stdout
    print(output_log)

    if contains_error(status_import):
        #Cloud location setup status results
        if not location_local:
            f = open(join(importer_directory, "ImportInstance_Status.txt"), "w")
            f.write("Complete_With_Errors")
            f.close()

    # Send email results
    results = "Success"
    if contains_error(status_import) or contains_error(status_export):
        results = "Error"
    subject = "{}-{} Salesforce Importer Results - {}".format(client_type, client_subtype, results)

    try:
        send_email(client_emaillist, subject, file_path, emailattachments, importer_log_directory)
    except Exception as ex:
        print("\nsend_email - Unexpected send email error:", str(ex))

    print("\nImporter process completed\n")

def process_data(importer_directory, salesforce_type, client_type,
                 client_subtype, operation, wait_time,
                 noexportsf, interactivemode, displayalerts, skipexcelrefresh, location_local,
                 updaterequired):
    """Process Data based on operation"""

    #Create log file for import status and reports
    from os import makedirs
    from os.path import exists, join
    file_path = importer_directory + "\\Status"
    if not exists(file_path):
        makedirs(file_path)

    output_log = "Process Data (" + operation + ")\n\n"
    status_process_data = ""

    # Export data from Salesforce

    try:
        if not noexportsf:
            status_process_data = export_dataloader(importer_directory,
                                                    salesforce_type, interactivemode, displayalerts, location_local, client_type, client_subtype)
        else:
            status_process_data = "Skipping export from Salesforce"
    except Exception as ex:
        output_log += "\n\nexport_dataloader - Unexpected error:" + str(ex)
        output_log += "\n\export_dataloader\n" + status_process_data
        status_process_data = "Error detected so skip processing - Exception"
    else:
        output_log += "\n\nExport\n" + status_process_data

    global stop_processing
    if stop_processing:
        return ""

    # Export data from Excel

    try:
        if (not skipexcelrefresh and not contains_error(status_process_data)
                and not contains_error(output_log.lower())):
            
            status_process_data = refresh_and_export(importer_directory,
                                                     salesforce_type, client_type,
                                                     client_subtype, operation,
                                                     wait_time, interactivemode, displayalerts)
            
        else:
            status_process_data = "Skipping refresh and export from Excel"
    except Exception as ex:
        output_log += "\n\nrefresh_and_export - Unexpected error:" + str(ex)
        output_log += "\n\refresh_and_export\n" + status_process_data
        status_process_data = "Error detected so skip processing - Exception"
    else:
        output_log += "\n\nExport\n" + status_process_data

    # Import Data into Salesforce

    if not "report" == operation.lower():

        try:
            if not contains_error(status_process_data) and not contains_error(output_log):
                status_process_data = import_dataloader(importer_directory,
                                                        client_type, salesforce_type,
                                                        operation,
                                                        updaterequired)
            else:
                print(status_process_data, output_log)
                status_process_data = "Error detected so skip processing"
        except Exception as ex:
            output_log += "\n\nrefresh_and_export - Unexpected error:" + str(ex)
            output_log += "\n\import_dataloader\n" + status_process_data
            status_process_data = "Error detected so skip processing - Exception"
        else:
            output_log += "\n\nImport\n" + status_process_data

    import datetime
    date_tag = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    with open(join(file_path, "Salesforce-Importer-Log-{}-{}.txt".format(operation, date_tag)),
              "w") as text_file:
        text_file.write(output_log)

    return status_process_data + output_log

def open_workbook(xlapp, xlfile):
    try:        
        xlwb = xlapp.Workbooks(xlfile)            
    except Exception as e:
        try:
            # workbooks.open(file, UpdateLinks = No, ReadOnly = True, Format = 2 Commas)
            xlwb = xlapp.Workbooks.Open(xlfile, 0, True, 2)
        except Exception as e:
            print(e)
            xlwb = None                    
    return(xlwb)

import time
from datetime import datetime

def wait_for_excel_refresh(excel_app, workbook, poll_seconds=1.0, timeout=1800, log_every=30):
    """
    Wait until Excel finishes refreshing.
    Logs start time + periodic status (elapsed + what's still refreshing).
    """
    started_at = datetime.now()
    start = time.time()
    last_log = 0

    print(f"[{started_at:%Y-%m-%d %H:%M:%S}] Excel refresh wait START")

    has_async_wait = hasattr(excel_app, "CalculateUntilAsyncQueriesDone")

    def _still_refreshing_details():
        """Return (any_refreshing: bool, details: list[str])"""
        details = []
        any_refreshing = False

        # Workbook-level flag (not always present/accurate on older Excel)
        try:
            if bool(getattr(workbook, "Refreshing")):
                any_refreshing = True
                details.append("Workbook.Refreshing=True")
        except Exception:
            pass

        # Connections
        try:
            for c in workbook.Connections:
                cname = ""
                try:
                    cname = getattr(c, "Name", "") or ""
                except Exception:
                    cname = ""

                # OLEDB / ODBC
                try:
                    if hasattr(c, "OLEDBConnection") and c.OLEDBConnection.Refreshing:
                        any_refreshing = True
                        details.append(f"Connection (OLEDB) refreshing: {cname}")
                except Exception:
                    pass
                try:
                    if hasattr(c, "ODBCConnection") and c.ODBCConnection.Refreshing:
                        any_refreshing = True
                        details.append(f"Connection (ODBC) refreshing: {cname}")
                except Exception:
                    pass

                # Power Query connections sometimes expose a generic Refreshing
                try:
                    if hasattr(c, "Refreshing") and bool(getattr(c, "Refreshing")):
                        any_refreshing = True
                        details.append(f"Connection refreshing: {cname}")
                except Exception:
                    pass
        except Exception:
            pass

        # QueryTables (legacy, but common)
        try:
            for ws in workbook.Worksheets:
                ws_name = ""
                try: ws_name = ws.Name
                except Exception: ws_name = "Sheet(?)"

                try:
                    for qt in ws.QueryTables:
                        try:
                            if qt.Refreshing:
                                any_refreshing = True
                                qt_name = ""
                                try: qt_name = getattr(qt, "Name", "") or ""
                                except Exception: qt_name = ""
                                details.append(f"QueryTable refreshing: {ws_name} / {qt_name}")
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass

        return any_refreshing, details

    while True:
        # Let Excel keep working
        try:
            excel_app.Calculate()
        except Exception:
            pass

        # Try waiting for async queries (Excel 2010+; works in many cases)
        if has_async_wait:
            try:
                excel_app.CalculateUntilAsyncQueriesDone()
            except Exception:
                pass

        any_refreshing, details = _still_refreshing_details()

        elapsed = time.time() - start

        # Heartbeat logging
        if elapsed - last_log >= log_every:
            last_log = elapsed
            now = datetime.now()
            print(f"[{now:%Y-%m-%d %H:%M:%S}] Still waiting... elapsed={int(elapsed)}s")
            if details:
                # Keep log readable: show up to first 10 items
                for line in details[:10]:
                    print("  - " + line)
                if len(details) > 10:
                    print(f"  ... +{len(details) - 10} more")
            else:
                print("  (No specific refreshing items detected; Excel may be busy calculating.)")

        # Done?
        if not any_refreshing:
            finished_at = datetime.now()
            print(f"[{finished_at:%Y-%m-%d %H:%M:%S}] Excel refresh wait DONE (elapsed={int(elapsed)}s)")
            return

        # Safety timeout
        if elapsed > timeout:
            now = datetime.now()
            msg = f"[{now:%Y-%m-%d %H:%M:%S}] Timeout waiting for Excel refresh (elapsed={int(elapsed)}s)"
            print(msg)
            if details:
                print("Still refreshing (last seen):")
                for line in details[:20]:
                    print("  - " + line)
            raise TimeoutError(msg)

        time.sleep(poll_seconds)

def wait_for_mashup_idle(cpu_threshold_total=5.0, settle_seconds=10, timeout=900, log_every=30):
    """
    Wait until all Microsoft.Mashup.Container* processes are collectively
    below `cpu_threshold_total` % CPU for `settle_seconds` consecutive 1-sec samples.
    Logs start time + periodic status.
    Times out after `timeout` seconds.
    """
    import time
    from datetime import datetime

    try:
        import psutil
    except ImportError:
        # Best-effort fallback: just wait a short fixed time if psutil isn't installed
        started_at = datetime.now()
        print(f"[{started_at:%Y-%m-%d %H:%M:%S}] Mashup idle wait START (psutil not installed) -> sleeping 15s")
        time.sleep(15)
        finished_at = datetime.now()
        print(f"[{finished_at:%Y-%m-%d %H:%M:%S}] Mashup idle wait DONE (fallback)")
        return

    started_at = datetime.now()
    start = time.time()
    consecutive_ok = 0
    last_log = 0

    print(f"[{started_at:%Y-%m-%d %H:%M:%S}] Mashup idle wait START "
          f"(threshold_total={cpu_threshold_total}%, settle_seconds={settle_seconds}, timeout={timeout}s)")

    # Warm up psutil cpu percent to avoid first-call zeros/garbage
    mashup_procs = []
    for p in psutil.process_iter(['name']):
        name = (p.info.get('name') or '')
        if name.startswith('Microsoft.Mashup.Container'):
            mashup_procs.append(p)
            try:
                p.cpu_percent(interval=None)
            except Exception:
                pass

    while True:
        # Re-discover processes each loop (they come/go)
        mashup_procs = []
        for p in psutil.process_iter(['name']):
            name = (p.info.get('name') or '')
            if name.startswith('Microsoft.Mashup.Container'):
                mashup_procs.append(p)

        total = 0.0
        alive_count = 0

        # 1-second sample across all mashup processes
        for p in mashup_procs:
            try:
                total += p.cpu_percent(interval=1.0)
                alive_count += 1
            except Exception:
                # process ended or access denied; ignore
                pass

        if total <= cpu_threshold_total:
            consecutive_ok += 1
        else:
            consecutive_ok = 0

        elapsed = time.time() - start

        # Heartbeat logging
        if elapsed - last_log >= log_every:
            last_log = elapsed
            now = datetime.now()
            print(f"[{now:%Y-%m-%d %H:%M:%S}] Mashup CPU total={total:.2f}% "
                  f"procs={alive_count} consecutive_ok={consecutive_ok}/{settle_seconds} "
                  f"elapsed={int(elapsed)}s")

        # Consider "idle" once we've been under threshold for settle_seconds consecutive samples
        if consecutive_ok >= settle_seconds:
            finished_at = datetime.now()
            print(f"[{finished_at:%Y-%m-%d %H:%M:%S}] Mashup idle wait DONE "
                  f"(elapsed={int(elapsed)}s, last_total={total:.2f}%, procs={alive_count})")
            return

        if elapsed > timeout:
            now = datetime.now()
            msg = (f"[{now:%Y-%m-%d %H:%M:%S}] Timeout waiting for Mashup idle "
                   f"(elapsed={int(elapsed)}s, last_total={total:.2f}%, procs={alive_count})")
            print(msg)
            raise TimeoutError(msg)
        
def refresh_and_export(importer_directory, salesforce_type,
                       client_type, client_subtype, operation,
                       wait_time, interactivemode, displayalerts):
    """Refresh Excel connections"""

    import os
    import os.path
    import time
    import win32com.client as win32

    refresh_status = "refresh_and_export\n"

    excel_connection = win32.gencache.EnsureDispatch("Excel.Application")

    try:
        excel_connection.ErrorCheckingOptions.BackgroundChecking = False
    except Exception:
        pass    

    excel_connection.EnableEvents = False
    excel_connection.DisplayAlerts = False
    excel_connection.Interactive = False

    # Optional: hide Excel window (good for background automation)
    excel_connection.ScreenUpdating = False # or True if debugging
    excel_connection.Visible = False  # or True if debugging

    excel_file_path = importer_directory + "\\"
    excel_file = excel_file_path + client_type + "-" + client_subtype + "_" + salesforce_type + ".xlsx"

    global workbook
    workbook_assigned = False
    workbook_successful = False
    open_max_attempts = 5
    open_attempt = 0
    found_operation_sheet = True

    while open_attempt < open_max_attempts and found_operation_sheet:

        open_wait_time = wait_time
        open_attempt += 1

        message = "\nImport Process - Attempt " + str(open_attempt) + " of " + str(open_max_attempts) + " to open Excel: " + excel_file
        print(message)
        if not os.path.exists(excel_file):
            message = "Import Process - ERROR File does not exist: " + excel_file
            print(message)

        try:
            workbook = open_workbook(excel_connection, excel_file)

            workbook_assigned = True

            found_operation_sheet = False
            for sheet in workbook.Sheets:
                sheet_name_lower = sheet.Name.lower()
                if operation.lower() in sheet_name_lower:
                    found_operation_sheet = True
                    break

            if not found_operation_sheet:
                refresh_status += "No sheets matched the operation: " + operation + "\n"
                print(refresh_status)

            else:

                message = "\nImport Process - Pausing 10 seconds for Excel to load in the background (You can see Excel in Task Manager but will be hidden from the desktop for better performance)..."
                print(message)
                refresh_status += message + "\n"
                time.sleep(10)

                excel_connection.Calculate()
                workbook.ForceFullCalculation = True           # workbook-level flag
                excel_connection.CalculateFullRebuild()        # application-level rebuild

                #for connection in workbook.Connections:
                    #print connection.name
                    # BackgroundQuery does not work so have to do manually in Excel for each Connection
                    #connection.BackgroundQuery = False

                # RefreshAll is Synchronous iif
                #   1) Enable background refresh disabled/unchecked in xlsx for all Connections
                #   2) Include in Refresh All enabled/checked in xlsx for all Connections
                #   To verify: Open xlsx Data > Connections > Properties for each to verify
                message = "\nImport Process - Refreshing all connections..."
                print(message)
                refresh_status += message + "\n"

                # RefreshAll - if direct Salesforce connection then will prompt for username & password
                #       under a couple of scenarios and will block until creds updates
                #   Scenario 1: First time running automation on a particular machine.
                #       User needs to select Remember me or this Scenario will repeat
                #   Scenario 2: Salesforce Password changed
                #   Scenario 3: Excel I think has a 3 month expiration for the user cred cookie
                #
                # Avoid adding connections to Excel that require username/password
                #   (e.g., Salesforce, Database).
                #   Instead use Exporter to pull the data external to Excel.
                workbook.RefreshAll()

                message = "Waiting for Excel refresh to complete (connections/query tables/async queries)..."
                print(message)
                refresh_status += message + "\n"                

                # Wait until Excel says refresh is finished
                wait_for_excel_refresh(excel_connection, workbook, poll_seconds=1.0, timeout=1800, log_every=30)

                message = "wait_for_excel_refresh completed"
                print(message)
                refresh_status += message + "\n"                

                # wait_for_excel_refresh the sheet data is loaded, mashup just keep running for awhile so going to just save out sheets

                # Optional: ensure PQ/Mashup containers settle (your existing backstop)
               # wait_for_mashup_idle(cpu_threshold_total=5.0, settle_seconds=10, timeout=900)

               # message = "wait_for_mashup_idle completed"
               # print(message)
               # refresh_status += message + "\n"                

                open_wait_time = 0

                # Wait for excel to finish refresh (don't need this anymore if the previous waits are working)
                #message = ("Pausing " + str(open_wait_time) +
                #        " seconds to give Excel time to complete background query...")
        #                   "\n\t\t***if Excel background query complete then press any key to exit wait cycle")
                #print(message)
                #refresh_status += message + "\n"

        #        with KeyboardHook() as keyboard_hook:

                    #Clear the input buffer
        #            keyboard_hook.reset()

                while open_wait_time > 0:
                    if open_wait_time > 30:
                        time.sleep(30)

                        open_wait_time -= 30
                        message = ("\t" + str(open_wait_time) +
                                    " seconds remaining for Excel to complete background query...")
        #                               "\n\t\t***if Excel background query complete then press any key to exit wait cycle")
                        print(message)
                        refresh_status += message + "\n"

                #        TARGET = "Microsoft.Mashup.Container.Loader.exe"
                #        if wait_until_gone_windows(TARGET, retries=0, check_every=0):
                #            print("No {} processes running. Proceeding.".format(TARGET))
                #            #open_wait_time = 0
                #            #break
                #        else:
                #            print("Process still running {}.".format(TARGET))

                    else:
                        time.sleep(open_wait_time)
                        open_wait_time = 0
                        break

        #                if keyboard_hook.key_pressed():
        #                    print "\nUser interrupted wait cycle\n"
        #                    break

                
        #        TARGET = "Microsoft.Mashup.Container.Loader.exe"
        #        if wait_until_gone_windows(TARGET, retries=30, check_every=60):
        #            print("No {} processes running. Proceeding.".format(TARGET))
        #        else:
        #            print("Gave up after 30 retries waiting for {}.".format(TARGET))

                message = "Import Process - Refreshing all connections...Completed"
                print(message)
                refresh_status += message + "\n"

                if not os.path.exists(excel_file_path + "Import\\"):
                    os.makedirs(excel_file_path + "Import\\")

                update_sheet_found = False
                for sheet in workbook.Sheets:
                    sheet_name_lower = sheet.Name.lower()
                    if "update" in sheet_name_lower:
                        update_sheet_found = True
                        break

                for sheet in workbook.Sheets:

                    # Only export update, insert, upsert, delete, or report sheets
                    sheet_name_lower = sheet.Name.lower()
                    if ("update" not in sheet_name_lower
                            and "upsert" not in sheet_name_lower
                            and "insert" not in sheet_name_lower
                            and "delete" not in sheet_name_lower
                            and "report" not in sheet_name_lower):
                        continue

                    excel_connection.Sheets(sheet.Name).Select()
                    sheet_file = excel_file_path + "Import\\" + sheet.Name + ".csv"

                    message = "Exporting csv for sheet: " + sheet_file
                    print(message)
                    refresh_status += message + "\n"

                    # Save report to Status to get attached to email
                    if "report" in sheet.Name.lower():

                        # Check if Manifest meaning report needs to be split  up
                        if "manifest" in sheet.Name.lower():

                            sheet_file = ""
                            process_manifest(workbook, sheet.Name, excel_file_path + "Status\\")
                        else:
                            sheet_file = excel_file_path + "Status\\" + sheet.Name + ".csv"

                    # Check for existing file
                    if os.path.isfile(sheet_file):
                        os.remove(sheet_file)

                    # By Design - set displayalerts before saveas so not prompting w/ save dialogs during automation.  Moved this here so that any RefreshAll errors will still surface and cause the refresh process not to finish thus an error will be detected
                    #excel_connection.DisplayAlerts = displayalerts

                    if not sheet_file == "":
                        workbook.SaveAs(sheet_file, 6)

                    # Update check to make sure insert sheet is empty
                    if (operation == "Update"
                            and update_sheet_found
                            and "insert" in sheet.Name.lower()
                            and contains_data(sheet_file)):

                        raise Exception("refresh_and_export: Update Error", (
                            "Insert sheet contains data and should be empty during update process: " +
                            sheet_file))

            workbook_successful = True

        except Exception as ex:
            message += "Unexpected error:" + str(ex)
            print(message)
            refresh_status += message + "\n"

            if open_attempt >= open_max_attempts:
                excel_connection.Quit()
                raise Exception("refresh_and_export", refresh_status)

            message = "\nImport Process - Pausing 10 seconds for system to recover from error..."
            print(message)
            refresh_status += message + "\n"
            time.sleep(10)

        finally:
            if not workbook is None and workbook_assigned:
                workbook.Close(False)

            workbook_assigned = False

            if workbook_successful:
                break;


    # Reset before quit
    excel_connection.ScreenUpdating = True
    excel_connection.EnableEvents = True
    excel_connection.DisplayAlerts = True
    excel_connection.Interactive = True

    excel_connection.Quit()

    return refresh_status

import subprocess
import time

CREATE_NO_WINDOW = 0x08000000  # hide console window

def any_running_tasklist(name):
    """
    Return True if a process with the given image name is running (Windows).
    Handles the '*32' suffix used by tasklist for 32-bit processes.
    """
    target = name.lower()
    target_star32 = (name + " *32").lower()

    # Fast path: filtered, CSV, no header
    try:
        out = subprocess.check_output(
            ["tasklist", "/FI", "IMAGENAME eq " + name, "/FO", "CSV", "/NH"],
            creationflags=CREATE_NO_WINDOW
        ).decode("utf-8", "ignore").strip()
        if out and not out.startswith("INFO:"):
            # First CSV field is the Image Name, inside quotes
            first_field = out.splitlines()[0].split('","', 1)[0].strip('"').lower()
            if first_field == target or first_field == target_star32:
                return True
    except Exception:
        pass  # fall through to the unfiltered check

    # Fallback: unfiltered scan (handles '*32' and localization)
    try:
        out = subprocess.check_output(
            ["tasklist"],
            creationflags=CREATE_NO_WINDOW
        ).decode("utf-8", "ignore").lower()
    except Exception:
        # Be conservative if tasklist fails
        return True

    for line in out.splitlines():
        line = line.strip()
        if not line or line.startswith("image name") or line.startswith("="):
            continue
        img = line.split()[0]  # first token is image name
        if img == target or img == target_star32:
            return True
    return False


def wait_until_gone_windows(name, retries=30, check_every=60):
    """
    Returns True when the process is NOT running.
    One immediate check, then up to `retries` more checks,
    sleeping `check_every` seconds between them.
    - retries=0 → exactly one check
    - check_every can be 0 for no delay
    """
    # Initial check
    if not any_running_tasklist(name):
        return True

    # Additional retries
    for _ in range(retries):
        if check_every:
            time.sleep(check_every)
        if not any_running_tasklist(name):
            return True

    return False

# workbook details: https://learn.microsoft.com/en-us/office/vba/api/excel.workbook
def process_manifest(workbook, sheet_name, statusDirectory):

    import csv
    import pandas as pd
    print("The Version of Pandas is: ", pd.__version__)
    import sys
    import os
    import os.path
    from os import listdir, makedirs
    from datetime import datetime

    #Create temp directory
    tempDirectory = os.path.join(statusDirectory, "temp\\")
    if not os.path.exists(tempDirectory):
        makedirs(tempDirectory)
    
    sheetFile = os.path.join(tempDirectory, sheet_name + ".csv")

    print("process_manifest: ", sheetFile)

    # Check for existing file
    if os.path.isfile(sheetFile):
        os.remove(sheetFile)

    workbook.SaveAs(sheetFile, 6)
    data = pd.read_csv(sheetFile)

    dateToday = datetime.today()

    for (cruiseID, cruiseDate), group in data.groupby(['Cruise ID', 'Cruise Date']):

        cruiseDateValue = datetime.strptime(cruiseDate, "%m/%d/%Y")
        daysDifference = abs((cruiseDateValue - dateToday).days)

        manifestType = "Preliminary"
        if daysDifference <= 10:
            manifestType = "Final"

        groupFileName = os.path.join(statusDirectory, "{}-{}-{}.csv".format(sheet_name, cruiseID, manifestType))
        group.to_csv(groupFileName, index=False)

import csv

def contains_data(file_name: str) -> bool:
    """
    True if CSV has at least one non-empty data row after header.
    Tries UTF-8 first, then falls back to cp1252 and latin-1.
    """
    encodings = ["utf-8-sig", "cp1252", "latin-1"]

    last_ex = None
    for enc in encodings:
        try:
            with open(file_name, newline="", encoding=enc, errors="strict") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                if not header:
                    return False
                for row in reader:
                    if any((cell or "").strip() for cell in row):
                        return True
                return False
        except Exception as ex:
            last_ex = ex
            continue

    # If we get here, we truly couldn't parse the file
    raise last_ex

def import_dataloader(importer_directory, client_type, salesforce_type, operation, updaterequired):
    """Import into Salesforce using DataLoader (.sdl + .csv)."""

    import os
    import time
    import subprocess
    from os import listdir
    from os.path import join, splitext, exists

    bat_path = join(importer_directory, "DataLoader")
    import_path = join(importer_directory, "Import")

    return_code = ""
    return_stdout = ""
    return_stderr = ""

    datafound = False
    sdl_files_found = 0

    # Helper: tolerant CSV "has rows?" check (handles cp1252/utf8 and bad bytes)
    def contains_data_tolerant(file_name):
        import csv
        # Try a couple common encodings; never fail hard
        encodings_to_try = ["utf-8-sig", "utf-8", "cp1252"]
        last_err = None

        for enc in encodings_to_try:
            try:
                with open(file_name, newline="", encoding=enc, errors="replace") as f:
                    reader = csv.reader(f)
                    header = next(reader, None)
                    if not header:
                        return False
                    for row in reader:
                        if any((cell or "").strip() for cell in row):
                            return True
                    return False
            except Exception as ex:
                last_err = ex

        # If we somehow still can’t read it, treat as "has data" so we attempt load rather than skipping silently
        print(f"DL CHECK: contains_data_tolerant WARNING for {file_name}: {last_err}")
        return True

    print(f"DL: operation={operation}")

    if not exists(bat_path):
        msg = f"DL: DataLoader folder not found: {bat_path}"
        print(msg)
        return "import_dataloader (returncode): 1\n" + msg

    for file_name in listdir(bat_path):

        if operation not in file_name or not file_name.lower().endswith(".sdl"):
            continue

        sdl_files_found += 1

        sheet_name = splitext(file_name)[0]
        import_file = join(import_path, sheet_name + ".csv")

        print(f"DL SCAN: file_name={file_name} operation={operation}")
        print(f"DL CHECK: looking for csv={import_file} exists={os.path.exists(import_file)}")

        # Skip if CSV missing
        if not os.path.exists(import_file):
            continue

        # Skip if CSV exists but has no rows
        try:
            has_rows = contains_data_tolerant(import_file)
            print(f"DL CHECK: contains_data={has_rows}")
        except Exception as ex:
            # Worst case: don’t crash; attempt the load
            print(f"DL CHECK: contains_data ERROR for {import_file}: {ex}")
            has_rows = True

        if not has_rows:
            continue

        datafound = True

        # IMPORTANT: Use cmd.exe /c to run the BAT reliably, and keep stdout/stderr as BYTES
        cmd = [
            "cmd.exe", "/c",
            join(bat_path, "RunDataLoader.bat"),
            salesforce_type,
            client_type,
            sheet_name
        ]

        message = f"Starting Import Process: {' '.join(cmd)} for file: {import_file}"
        print(message)
        return_stdout += message + "\n"

        # Small throttle can help with file handles / Java startup on busy servers
        time.sleep(1)

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False  # <-- critical: prevents the cp1252 readerthread UnicodeDecodeError
        )

        stdout_b, stderr_b = proc.communicate()

        # Decode safely (never crash on weird bytes)
        stdout = (stdout_b or b"").decode("utf-8", errors="replace")
        stderr = (stderr_b or b"").decode("utf-8", errors="replace")

        print(f"Finished Import Process: {sheet_name} returncode={proc.returncode}")

        return_code += f"import_dataloader (returncode): {proc.returncode}\n"
        if stdout.strip():
            return_stdout += "\n\nimport_dataloader (stdout):\n" + stdout + "\n"
        if stderr.strip():
            return_stderr += "\n\nimport_dataloader (stderr):\n" + stderr + "\n"

        # If you want “fail fast” on non-zero return codes, uncomment:
        # if proc.returncode != 0:
        #     raise Exception("Invalid Return Code", return_code + return_stdout + return_stderr)

    print(f"DL: operation={operation} sdl_files_found={sdl_files_found}")
    if not datafound:
        print(f"DL: No data found for operation={operation} (no matching CSVs with rows)")

    # Check if updaterequired
    if operation == "Update" and updaterequired and not datafound:
        raise Exception("Update operation and updaterequired but no data was found")

    return return_code + return_stdout + return_stderr

def export_dataloader(importer_directory, salesforce_type, interactivemode, displayalerts, location_local, client_type, client_subtype):
    
    """Export out of Salesforce using DataLoader"""

    from os.path import exists, join
    from subprocess import Popen, PIPE

    exporter_clientdirectory = importer_directory.replace("Importer", "Exporter")
    exporter_directory = exporter_clientdirectory
    if "\\Salesforce-Exporter\\" in exporter_directory:
        exporter_directory += "\\..\\..\\.."

    interactive_flag = ""
    if interactivemode:
        interactive_flag = "-interactivemode"
    bat_file = exporter_directory + "\\exporter.bat {} {}".format(salesforce_type, interactive_flag)

    return_code = ""
    return_stdout = ""
    return_stderr = ""

    if not exists(exporter_directory):
        print("Skip Export Process (export not detected)")
    else:
        message = "Starting Export Process: " + bat_file + "\n\nExport Process - can take up to a couple of minutes depending on your Internet connection..."
        print(message)
        return_stdout += message + "\n"
        export_process = Popen(bat_file, stdout=PIPE, stderr=PIPE)

        stdout, stderr = export_process.communicate()

        return_code += "\n\nexport_dataloader (returncode): " + str(export_process.returncode)
        return_stdout += "\n\nexport_dataloader (stdout):\n" + stdout
        return_stderr += "\n\nexport_dataloader (stderr):\n" + stderr

        if (export_process.returncode != 0
                or contains_error(return_stdout)
                or "We couldn't find the Java Runtime Environment (JRE)" in return_stdout):
            raise Exception("Invalid Return Code", return_code + return_stdout + return_stderr)

    #Check to extract the data from the content version if running in the cloud
    if not location_local:
        if not export_extractcontentexists(importer_directory, client_type, client_subtype):
            
            print("\nRunning in Cloud and no valid Import Instance so skip processing\n")
            global stop_processing
            stop_processing = True

    return return_code + return_stdout + return_stderr

def export_extractcontentexists(importer_directory, client_type, client_subtype):

    """Export - extract content exists - checks to see if running on cloud if there is any content scheduled for import"""
    import base64
    from csv import DictReader
    from os.path import join
    import sys
    import csv
    import os
    from subprocess import Popen, PIPE

    exporter_clientdirectory = join(importer_directory.replace("Importer", "Exporter"), "Export\\")
    linked_entity_ids = set()

    try:
        global emailattachments
        validImportInstance = False

        # Check for scheduled import instance
        with open(join(exporter_clientdirectory,'ImportInstanceExtract-Prod.csv'), 'r') as read_obj:
            csv_dict_reader = DictReader(read_obj)
            for row in csv_dict_reader:

                #Check for schedule related to current client
                if row['TYPE__C'] in client_subtype:

                    #Valid Import Instance but no files required so return without attempting to extract files
                    if row['EMAIL_ATTACH_LOGS__C'] == 'All Logs':
                        emailattachments = True
                    else:
                        emailattachments = False

                    validImportInstance = True
                    break

        # No valid import instance so return to kick out of process until there is a valid instance
        if not validImportInstance:
            return False

        # Attempt to extract file data
        with open(join(exporter_clientdirectory, 'ContentDocumentLinkExtract-Prod.csv'), 'r') as read_obj:
            csv_dict_reader = DictReader(read_obj)
            for row in csv_dict_reader:

                linked_entity_ids.add("'" + row['LINKEDENTITYID'] + "'")

    except Exception as ex:
        print("\nexport_extractcontent - Unexpected error:", str(ex))

    if len(linked_entity_ids) <= 0:
        return True

    #run extract
    comma_list = ",".join(linked_entity_ids)
    p = Popen(['python', r'C:\repo\salesforce-files-download\download.py', '-o', exporter_clientdirectory, '-q', comma_list, '-t', client_type],
              stdout=PIPE,
              stderr=PIPE,
              cwd=r'C:\repo\salesforce-files-download')
    output = p.communicate()
    print(output[0])

    return True

def export_postgres(importer_directory, salesforce_type, client_subtype, client_emaillist, interactivemode, displayalerts):
    """Export out of Postgres"""

    from os.path import exists
    from subprocess import Popen, PIPE

    exporter_directory = importer_directory.replace("Salesforce-Importer", "Postgres-Exporter")
    if "\\Postgres-Exporter\\" in exporter_directory:
        exporter_directory += "\\..\\..\\.."

    interactive_flag = ""
    if (interactivemode or displayalerts):
        interactive_flag = "-interactivemode"
    bat_file = exporter_directory + "\\exporter.bat {} {} iTravel {} {}".format(salesforce_type,
                                                                     client_subtype,
                                                                     client_emaillist,
                                                                     interactive_flag)

    return_code = ""
    return_stdout = ""
    return_stderr = ""

    if not exists(exporter_directory):
        print("Skip Postgres Export Process (export not detected)")
    else:
        message = "Starting Postgres Export Process: " + bat_file
        print(message)
        return_stdout += message + "\n"
        export_process = Popen(bat_file, stdout=PIPE, stderr=PIPE)

        stdout, stderr = export_process.communicate()

        return_code += "\n\nexport_postgres (returncode): " + str(export_process.returncode)
        return_stdout += "\n\nexport_postgres (stdout):\n" + stdout
        return_stderr += "\n\nexport_postgres (stderr):\n" + stderr

        if (export_process.returncode != 0
                or contains_error(return_stdout)
                or "We couldn't find the Java Runtime Environment (JRE)" in return_stdout):
            raise Exception("Invalid Return Code", return_code + return_stdout + return_stderr)

    return return_code + return_stdout + return_stderr

def export_odbc(importer_directory, salesforce_type, client_subtype, interactivemode, displayalerts):
    """Export out of ODBC"""

    from os.path import exists
    from subprocess import Popen, PIPE

    exporter_directory = importer_directory.replace("Salesforce-Importer", "ODBC-Exporter")
    if "\\ODBC-Exporter\\" in exporter_directory:
        exporter_directory += "\\..\\..\\.."

    interactive_flag = ""
    if (interactivemode or displayalerts):
        interactive_flag = "-interactivemode"
    bat_file = exporter_directory + "\\exporter.bat {} {} {}".format(salesforce_type,
                                                                     client_subtype,
                                                                     interactive_flag)

    return_code = ""
    return_stdout = ""
    return_stderr = ""

    if not exists(exporter_directory):
        print("Skip ODBC Export Process (export not detected)")
    else:
        message = "Starting ODBC Export Process: " + bat_file
        print(message)
        return_stdout += message + "\n"
        export_process = Popen(bat_file, stdout=PIPE, stderr=PIPE)

        stdout, stderr = export_process.communicate()

        return_code += "\n\nexport_odbc (returncode): " + str(export_process.returncode)
        return_stdout += "\n\nexport_odbc (stdout):\n" + stdout
        return_stderr += "\n\nexport_odbc (stderr):\n" + stderr

        if (export_process.returncode != 0
                or contains_error(return_stdout)
                or "We couldn't find the Java Runtime Environment (JRE)" in return_stdout):
            raise Exception("Invalid Return Code", return_code + return_stdout + return_stderr)

    return return_code + return_stdout + return_stderr

import re

def contains_error(text: str) -> bool:
    """
    True if text likely indicates a real failure.

    This is intentionally conservative:
      - catches Tracebacks/Exceptions/Invalid Return Code/returncode != 0
      - ignores common benign strings that include 'error' (e.g., '0 errors')
    """
    if not text:
        return False

    t = str(text).lower()

    # Normalize a couple things that commonly trigger false positives
    t = t.replace("0 errors", "0_errors")  # prevent matching 'errors' patterns
    t = t.replace("no data found", "no_data_found")

    # Benign / expected phrases that should NOT trigger Error status
    ignore_patterns = [
        r"\b0_errors\b",
        r"no_data_found",
        r"no sheets matched the operation",
        r"skipping refresh and export from excel",
        r"skipping export from salesforce",
        r"skip postgres export process",
        r"skip odbc export process",
        r"syntaxwarning: invalid escape sequence",   # Python warning, not fatal
    ]
    for pat in ignore_patterns:
        if re.search(pat, t):
            # Don't return yet; we still might have a real error elsewhere.
            # We'll just remove these phrases from consideration.
            t = re.sub(pat, "", t)

    # Hard-fail signals (these should always mean "Error")
    hard_fail_patterns = [
        r"\btraceback\b",
        r"\bexception\b",
        r"\bfatal\b",
        r"\binvalid return code\b",
        r"\baccess denied\b",
        r"\blogin failed\b",
        r"\bauthentication\b.*\bfailed\b",
        r"\bwe couldn't find the java runtime environment\b",
        r"\btimeout waiting\b",
        r"\breturncode\s*[:=]\s*[1-9]\d*\b",   # returncode: 2, returncode=1, etc.
        r"\bimport_process.*returncode\s*[:=]\s*[1-9]\d*\b",
        r"\berror\b.*\bdetected\b",
    ]

    for pat in hard_fail_patterns:
        if re.search(pat, t):
            return True

    # If the word 'error' still appears, only treat as error if it looks like a log marker
    # (e.g., "ERROR:", "Unexpected error", etc.)
    soft_fail_patterns = [
        r"\berror\s*:",
        r"\bunexpected error\b",
        r"\berror while\b",
        r"\berror calling\b",
    ]
    for pat in soft_fail_patterns:
        if re.search(pat, t):
            return True

    return False

def file_linecount(file_name):
    """Count how many lines after the header (binary-safe)."""
    line_index = -1  # header not counted
    with open(file_name, "rb") as f:
        for line in f:
            if line:
                line_index += 1
    return line_index

def send_email(client_emaillist, subject, file_path, emailattachments, log_path):
    """Send email via O365 (robust recipients + attachment handling + encoding-safe)."""

    import base64
    from email.mime.application import MIMEApplication
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.utils import COMMASPACE, formatdate
    import os
    from os.path import basename, join, exists, splitext, isfile
    from shutil import copy
    import smtplib
    import re
    import time

    print("\n\nPreparing email results\n")

    # Parse recipients
    send_to = [x.strip() for x in client_emaillist.split(";") if x.strip()]

    send_from = os.environ.get("SERVER_EMAIL_USERNAME", "daveb@uncruise.com")
    smtp_host = os.environ.get("SERVER_EMAIL", "smtp.office365.com")

    msg = MIMEMultipart()
    msg["From"] = send_from
    msg["Date"] = formatdate(localtime=True)
    msg["Subject"] = subject

    msgbody = subject + "\n\n"
    if not emailattachments:
        msgbody += "Attachments disabled: Result files can be accessed on the import client.\n\n"

    # Default: admin-only until we see at least one CSV (a true “load attempt”)
    sendTo_AdminOnly = True
    sendTo_AdminAddress = "itreports@uncruise.com"

    for sendToEmail in send_to:
        if re.search("uncruise", sendToEmail, re.IGNORECASE):
            sendTo_AdminAddress = sendToEmail
            break

    # Decide actual SMTP recipients (IMPORTANT: use this list in sendmail)
    smtp_recipients = [sendTo_AdminAddress]  # may be replaced later

    # Helper: tolerant “has data” check that won’t blow up on cp1252 smart chars
    def contains_data_tolerant(path):
        import csv
        encodings_to_try = ["utf-8-sig", "utf-8", "cp1252"]
        for enc in encodings_to_try:
            try:
                with open(path, newline="", encoding=enc, errors="replace") as f:
                    reader = csv.reader(f)
                    header = next(reader, None)
                    if not header:
                        return False
                    for row in reader:
                        if any((cell or "").strip() for cell in row):
                            return True
                    return False
            except Exception:
                continue
        # If we can't read it cleanly, assume it has data so we don't skip silently.
        return True

    if file_path:
        onlyfiles = [
            join(file_path, f) for f in os.listdir(file_path)
            if isfile(join(file_path, f))
        ]

        msgbody += f"Log Directory: {log_path}\n\n"

        for full_path in onlyfiles:
            # Skip already-marked files
            if ".sent" in full_path:
                continue

            # This was your main driver for “only attach if contains_data”
            # Use tolerant check to avoid UTF-8 decode crashes.
            if not contains_data_tolerant(full_path):
                continue

            # Describe file and row count (binary-safe file_linecount already)
            msgbody += f"\t{basename(full_path)}, with {file_linecount(full_path)} rows\n"

            # If we have a CSV, we consider this a real “load attempt” -> allow full distro
            if full_path.lower().endswith(".csv"):
                sendTo_AdminOnly = False

            # Attachment rules (same intent as yours, but keep it simple)
            should_attach = (
                emailattachments
                or (contains_error(subject) and "log" in full_path.lower())
                or contains_error(full_path.lower())
            )

            if should_attach:
                with open(full_path, "rb") as f:
                    part = MIMEApplication(f.read(), Name=basename(full_path))
                part["Content-Disposition"] = f'attachment; filename="{basename(full_path)}"'
                msg.attach(part)

            # Rename to .sent.ext so it won't attach again
            filename, ext = splitext(full_path)
            sent_path = f"{filename}.sent{ext}"

            if exists(sent_path):
                os.remove(sent_path)

            os.rename(full_path, sent_path)

            # Save copy to log directory
            try:
                copy(sent_path, log_path)
            except Exception as ex:
                # Don’t fail email just because copy failed
                msgbody += f"\n\tWARNING: could not copy {basename(sent_path)} to log dir: {ex}\n"

    # Build To header + SMTP recipients list (IMPORTANT)
    if sendTo_AdminOnly:
        msg["To"] = sendTo_AdminAddress
        smtp_recipients = [sendTo_AdminAddress]
    else:
        msg["To"] = COMMASPACE.join(send_to)
        smtp_recipients = send_to

    # Add version footer
    importer_py = join(file_path, "..\\..\\..\\importer.py") if file_path else None
    if importer_py and exists(importer_py):
        msgbody += "\n\nAdventure Ready Consulting ETL Version: %s\n\n" % format(
            time.ctime(os.path.getmtime(importer_py))
        )

    print(msgbody)
    msg.attach(MIMEText(msgbody, _subtype="plain", _charset="utf-8"))

    # SMTP auth
    server_password = os.environ.get("SERVER_EMAIL_PASSWORD", "unknown")
    server_password = os.environ.get("SERVER_EMAIL_PASSWORDOVERRIDE", server_password)

    if isinstance(server_password, bytes):
        server_password = server_password.decode("utf-8", errors="replace")

    # Be defensive: if it's not base64, allow plaintext password too
    decoded_pw = None
    try:
        decoded_pw = base64.b64decode(server_password).decode("utf-8", errors="replace")
    except Exception:
        decoded_pw = server_password

    smtp = smtplib.SMTP(smtp_host, 587)
    smtp.starttls()
    smtp.login(send_from, decoded_pw)

    text = msg.as_string()

    # IMPORTANT: send to smtp_recipients (matches admin-only logic)
    smtp.sendmail(send_from, smtp_recipients, text)
    smtp.quit()

    print("\nSent email results\n")

def send_salesforce():
    """Send results to Salesforce to handle notifications"""
    #Future update to send to salesforce to handle notifications instead of send_email
    #https://developer.salesforce.com/blogs/developer-relations/2014/01/
    #python-and-the-force-com-rest-api-simple-simple-salesforce-example.html

if __name__ == "__main__":
    main()