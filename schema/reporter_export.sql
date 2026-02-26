
  COPY(
      SELECT
          name, split_part(default_connection, ',', 1),
          district, facility, groups, active,  get_contact_facility_code(id) AS facility_code
      FROM reporters WHERE active='t' AND length(default_connection) > 12 AND facility_code NOT like 'gen%'
  ) TO '/tmp/reporters.csv' WITH DELIMITER '#' CSV HEADER;



