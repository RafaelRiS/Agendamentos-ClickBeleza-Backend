class Scheduler:

    def __init__(self, database):
        self.db = database

        def get_available_slots(self, barber_id, date, duration):
            appointments = self.db.get_appointments(barber_id, date)

            # lógica para calcular horários livres
            return []

