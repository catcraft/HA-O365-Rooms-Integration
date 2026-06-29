class RoomOccupiedBinarySensor(CoordinatorEntity, BinarySensorEntity):
    _attr_name = "Meeting Aktiv"

    @property
    def is_on(self):
        return self.coordinator.data.get("occupied", False)
