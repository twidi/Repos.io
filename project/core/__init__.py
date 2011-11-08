REDIS_KEYS = dict(
    last_fetched = 'last_fetched_%s',
)

for key in REDIS_KEYS.keys():
    REDIS_KEYS[key] = dict(
        account = REDIS_KEYS[key] % 'accounts',
        repository = REDIS_KEYS[key] % 'repositories'
    )

