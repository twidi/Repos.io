REDIS_KEYS = dict(
    last_fetched = 'last_fetched_%s',
    best_scored  = 'best_scored_%s',
    public_tags = 'public_tags_%s_%%d',
)

for key in REDIS_KEYS.keys():
    REDIS_KEYS[key] = dict(
        account = REDIS_KEYS[key] % 'accounts',
        repository = REDIS_KEYS[key] % 'repositories'
    )

