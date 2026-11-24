CREATE TABLE IF NOT EXISTS rehearsal_venues (
 code text PRIMARY KEY,title text NOT NULL, covered boolean NOT NULL, max_heads int NOT NULL CHECK(max_heads>0),
 rate_per_half int NOT NULL CHECK(rate_per_half>=0), neighborhood text NOT NULL
);
CREATE TABLE IF NOT EXISTS historical_blocks (
 on_day date, half_from smallint CHECK(half_from BETWEEN 0 AND 47),
 temp_c real NOT NULL CHECK(temp_c BETWEEN -15 AND 55), humidity int NOT NULL CHECK(humidity BETWEEN 0 AND 100),
 source text NOT NULL, PRIMARY KEY(on_day,half_from)
);
CREATE TABLE IF NOT EXISTS practice_holds (
 code text PRIMARY KEY,title text NOT NULL,on_day date NOT NULL, original text NOT NULL REFERENCES rehearsal_venues(code),
 backup text NOT NULL REFERENCES rehearsal_venues(code), from_block smallint NOT NULL,to_block smallint NOT NULL,
 heads int NOT NULL CHECK(heads>0),state text NOT NULL CHECK(state IN ('held','proposed','closed')),
 CHECK(0<=from_block AND from_block<to_block AND to_block<=48),CHECK(original<>backup)
);
CREATE TABLE IF NOT EXISTS analog_replays (
 code text PRIMARY KEY REFERENCES practice_holds(code), percentile real NOT NULL CHECK(percentile BETWEEN 0 AND 1),
 neighbors int NOT NULL CHECK(neighbors>=2), replay_window jsonb NOT NULL, backtest jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS adjustment_vouchers (
 hold text PRIMARY KEY REFERENCES practice_holds(code), from_block smallint NOT NULL,to_block smallint NOT NULL,
 moved_to text NOT NULL REFERENCES rehearsal_venues(code), estimate_cents int NOT NULL CHECK(estimate_cents>=0),
 memo text NOT NULL, reviewed_by text NOT NULL, settled_by text, settled_at timestamptz,
 CHECK(0<=from_block AND from_block<to_block AND to_block<=48)
);
