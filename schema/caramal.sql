INSERT INTO dhis2_mtrack_indicators_mapping
    (form, slug, cmd, form_order, description, dataset, dataelement, category_combo)
    VALUES
    ('car', 'car_patients_seen', 'patients_seen', 0, 'Number of patients seen', 'kzIS9qjcF6W', 'iIO5V7PJJwe', 'bjDvmb4bfuf'),
    ('car', 'car_patients_with_fever', 'patients_with_fever', 1, 'Number of patients with fever', 'kzIS9qjcF6W', 'phxagKD2YUi', 'bjDvmb4bfuf'),
    ('car', 'car_rdt_positive', 'rdt_positive', 2, 'Number of RDT +ve patients', 'kzIS9qjcF6W', 'y3khdxvLfpG', 'bjDvmb4bfuf'),
    ('car', '', 'car_patients_with_danger_signs', 3, 'Number of patients with danger signs', 'kzIS9qjcF6W', 'mY5azRcJKpw', 'bjDvmb4bfuf'),
    ('car', 'car_patients_receiving_ras', 'patients_receiving_ras', 4, 'Number of patients receiving RAS', 'kzIS9qjcF6W', 'NFSEQwngr5o', 'bjDvmb4bfuf'),

    ('ras', 'ras_patient_id', 'patient_id', 0, 'Patient ID', 'kzIS9qjcF6W', 'n9ZzKfqxIAk', 'bjDvmb4bfuf'),
    ('ras', 'ras_patient_age', 'patient_age', 1, 'Patient Age', 'kzIS9qjcF6W', 'admpnpCyyyS', 'bjDvmb4bfuf'),
    ('ras', 'ras_patient_sex', 'patient_sex', 2, 'Patient Sex', 'kzIS9qjcF6W', 'IM4qZpgowPm', 'bjDvmb4bfuf');
