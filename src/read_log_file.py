#       read_log_file.py
#
#   Given a log file, parse through that file and return a gc_events_dataframe containing all
#   relevant information from the log during runtime
#
#   Ellis Brown, 6/29/2021

import pandas as pd
import re


## # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
#                               get_parsed_data_from_file
#
# Purpose:
#   Given a filepath to a log file, create a pandas dataframe holding all information
#   for that log file. Each row is a different event.
#
# Parameters:
#   logfile -> a string with the path to the log file to read.
#
# Return:
#   a pandas dataframe, where rows are each an individual event. Columns are labeled, and
#   collect information on each event, such as when it occured, how long it lasted, and the name
## # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
def get_parsed_data_from_file(logfile, time_range_seconds=None):
    assert isinstance(logfile, str)  # input must be a string

    if not logfile:
        print("No logfile provided")
        return
    table = __manyMatch_LineSearch(event_parsing_string(), logfile)
    if not any(table):
        print("Unable to parse file " + str(logfile))
        return None
    # Convert the paused and time from start from string datatypes to floats
    table[1] = list(map(__number_to_float, table[1]))
    table[6] = list(map(__number_to_float, table[6]))
    parsed_data_table = pd.DataFrame(table).transpose()  # transpose to orient correctly
    parsed_data_table.columns = __columnNames()  # add column titles, allow for clear references
    if time_range_seconds:
        min_time, max_time = __get_time_range(time_range_seconds)
        # Get the maximum and minimums and enforce the time range
        in_minimum = parsed_data_table["TimeFromStart_seconds"] >= min_time
        in_maximum = parsed_data_table["TimeFromStart_seconds"] <= max_time
        # Create the combined time table
        parsed_data_table = parsed_data_table[in_minimum & in_maximum]
    return parsed_data_table


def __get_time_range(time_range):
    if type(time_range) == int or type(time_range) == float:
        min_time = 0
        max_time = time_range
    else:
        #   assert len(time_range) == 2
        min_time = time_range[0]
        max_time = time_range[1]
    return min_time, max_time


def __number_to_float(number):
    if number != None:
        return float(number)
    return None


## # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
#                         __manyMatch_LineSearch
#   Purpose:
#       Search through a file and return a list of matches for a regex search term
#
#   Parameters:
#       search_term      : string-> Terms to search for within data set
#       filepath         : string-> file path to log file
#   Return:
#       2 dimensional list structure. List of group's matches
#       table[index] = list of all matches associated with group at index - 1
#
## # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
def __manyMatch_LineSearch(
    match_term=None,  # regex terms to search for
    filepath=None,
):  # TRUE if data in a file
    num_match_groups = re.compile(match_term).groups
    table = [[] for i in range(num_match_groups)]
    # If there has been listed groups of interest within the regex search
    file = open(filepath, "r")
    for line in file:
        match = re.search(match_term, line)
        if match:
            # Find all matches of interest
            for i in range(0, num_match_groups):
                table[i].append(match.group(i + 1))  # +1 because group(0) is the whole string
            # add the match group number hit, so able to tell what match
    file.close()
    return table


# Access the column names for a parsed file. Note that these are dependent
# on the groups defined in event_string_parsing
def __columnNames():
    return [
        "DateTime",
        "TimeFromStart_seconds",
        "EventType",
        "EventName",
        "AdditionalEventInfo",
        "MemoryChange_MB",
        "Duration_miliseconds",
    ]


## # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
#                       event_parsing_string
#
# Returns a regex-searchable string to handle parsing log lines.
# Defined regex groups are each section of the code
#
# GROUP 1: "DateTime" -> information on time of recording
# GROUP 2: "TimeFromStart_seconds" -> time of beginning of event in seconds
# GROUP 3: "EventType" -> Either concurrent or stop the world pause
# GROUP 4: "EventName" -> Specific action from the event. Example : "(pause) Young"
# GROUP 5: "AdditionalEventInfo" -> Information about the event
# GROUP 6: "MemoryChange_MB" -> Memory changed, following this patten: before->after(max_heapsize)
# GROUP 7: "Duration_miliseconds" -> How long it took for the event to occur in miliseconds
#
#  Return: string
## # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
def event_parsing_string():
    # note: Not all lines contain a regex-group. Group lines are commented with a *
    date_time = "^(?:\[(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}\+\d{4})\])?"  # [2021-07-01T23:23:22.001+0000]    *
    time_from_start_seconds = "\[(\d+\.\d+)s\]"  # [243.45s]     *
    gc_info_level = "\[\w+ *\]"  # [info ]
    type_gc_log_line = "\[gc(?:,\w+)?\s*\] "  # [gc, trace]
    gc_event_number = "GC\(\d+\) "  # GC(25)
    type_gc_event = "((?:Pause(?=.*ms))|(?:Concurrent(?=.*ms))|(?:Garbage Collection)) "  # Concurrent    *
    gc_event_name = "(?:((?:\w+ ?){1,3}) )?"  # Young    *
    gc_additional_info = "((?:\((?:\w+ ?){1,3}\) ){0,3})"  # (Evacuation Pause)    *
    heap_memory_change = "((?:(?:\d+\w->\d+\w(?:\(\d+\w\)?)?)?(?= ?"  # 254M->12M(1200M)    *
    time_spent_miliseconds = "(\d+\.\d+)ms))"  # 24.321ms    *
    zgc_style_heap_memory_change = "|(?:\d+\w\(\d+%\)->\d+\w\(\d+%\)))"  # 25M(4%)->12M(3%)    *
    event_regex_string = (
        date_time
        + time_from_start_seconds
        + gc_info_level
        + type_gc_log_line
        + gc_event_number
        + type_gc_event
        + gc_event_name
        + gc_additional_info
        + heap_memory_change
        + time_spent_miliseconds
        + zgc_style_heap_memory_change
    )
    return event_regex_string
