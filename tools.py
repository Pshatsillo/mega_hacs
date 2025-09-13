class FilterBadValues:

    def __init__(self, *args, **kwargs):
        self._prev_value = None
        super().__init__(*args, **kwargs)

    def filter_value(self, value):
        try:
            if value \
                    in self.filter_values \
                    or (self.filter_low is not None and value < self.filter_low) \
                    or (self.filter_high is not None and value > self.filter_high) \
                    or (
                    self._prev_value is not None
                    and self.filter_scale is not None
                    and (
                            abs(value - self._prev_value) / self._prev_value > self.filter_scale
                    )
            ):
                if self.fill_na == 'last':
                    value = self._prev_value
                else:
                    value = None
            self._prev_value = value
            return value
        except Exception as exc:
            lg.exception(f'while parsing value')
            return None

    @property
    def filter_values(self):
        return self.customize.get(CONF_FILTER_VALUES, self.mega.customize.get(CONF_FILTER_VALUES, []))

    @property
    def filter_scale(self):
        return self.customize.get(CONF_FILTER_SCALE, self.mega.customize.get(CONF_FILTER_SCALE, None))

    @property
    def filter_low(self):
        return self.customize.get(CONF_FILTER_LOW, self.mega.customize.get(CONF_FILTER_LOW, None))

    @property
    def filter_high(self):
        return self.customize.get(CONF_FILTER_HIGH, self.mega.customize.get(CONF_FILTER_HIGH, None))

    @property
    def fill_na(self):
        return self.customize.get(CONF_FILL_NA, 'last')