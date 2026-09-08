from database import appointments_collection


class Scheduler:

    def __init__(self):
        self.collection = appointments_collection

    def get_available_slots(self, barber, date, duration):
        appointments = self.collection.find({
            "barber": barber,
            "date": date
        })

        # Aqui entra a lógica para calcular os horários livres
        return []
