-- Run these in the weather-etl-dev Athena workgroup.
-- Partition projection is on, so filter ingest_date instead of running MSCK REPAIR.
-- ingest_date is the UTC day the pipeline ran. observation_time is the forecast hour.

-- Average temperature for the latest landed day.
SELECT
    location_id,
    avg(temperature_c) AS avg_temperature_c,
    sum(precipitation_mm) AS precipitation_mm
FROM weather_etl.hourly_observations
WHERE ingest_date = current_date
GROUP BY location_id
ORDER BY location_id;

-- Hours with rain, for one city and one pipeline date.
SELECT
    observation_time,
    temperature_c,
    precipitation_mm,
    wind_speed_kmh
FROM weather_etl.hourly_observations
WHERE ingest_date = DATE '2026-10-22'
  AND location_id = 'berlin'
  AND precipitation_mm > 0
ORDER BY observation_time;

-- Freshness check you can run after a scheduled execution.
-- A healthy daily batch has at least one row on the ingest date for every city.
SELECT
    ingest_date,
    location_id,
    count(*) AS hours,
    min(observation_time) AS first_hour,
    max(observation_time) AS last_hour
FROM weather_etl.hourly_observations
WHERE ingest_date >= current_date - INTERVAL '7' DAY
GROUP BY ingest_date, location_id
ORDER BY ingest_date DESC, location_id;
