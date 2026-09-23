
from .live_sync import sync_timetable_sources


class TimetableLiveSyncMiddleware:
    """
    Keeps Timetabling reference data synchronized with the
    main ERP whenever a Timetabling page is accessed.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        if request.path.startswith("/timetable/"):

            try:
                sync_timetable_sources()
            except Exception as exc:
                # Never prevent the timetable page from opening
                # because of a synchronization problem.
                print("TIMETABLE LIVE SYNC WARNING:", exc)

        return self.get_response(request)
