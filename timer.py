import threading
import time

timer_quit = threading.Event()


def create_timer_thread(callback):
    timer_quit.clear()
    return threading.Thread(
        target=timer_thread,
        kwargs={"callback": callback},
        daemon=True
    )


def format_time(hours, minutes, seconds):
    st_seconds = str(seconds)
    st_minutes = str(minutes)
    st_hours = str(hours)
    if len(st_seconds) == 1:
        st_seconds = "0" + st_seconds
    if len(st_minutes) == 1:
        st_minutes = "0" + st_minutes
    if len(st_hours) == 1:
        st_hours = "0" + st_hours
    return f"{st_hours}:{st_minutes}:{st_seconds}"


def timer_thread(callback):

    minutes = 0
    seconds = 0
    hours = 0

    while not timer_quit.is_set():
        time.sleep(1)
        seconds += 1
        if seconds > 60:
            seconds = 0
            minutes += 1
            if minutes > 60:
                hours += 1
                minutes = 0
        try:
            callback(format_time(hours, minutes, seconds))
        except RuntimeError as err:
            print(err.__str__())
