-- Create a New Database
-- CREATE DATABASE CDRI;

-- Connect to the Newly Created Database
USE cdri;

-- Create CelestialItems Table
CREATE TABLE CelestialItems (
    id serial PRIMARY KEY,
    item_name text,
    item_type text,
    discovery_date date,
    celestial_coordinates point,
    description text
);

-- Create Researchers Table
CREATE TABLE Researchers (
    id serial PRIMARY KEY,
    full_name text,
    specialization text,
    email text
);

-- Create AlienEncounters Table
CREATE TABLE AlienEncounters (
    id serial PRIMARY KEY,
    encounter_date date,
    location_coordinates point,
    description text
);

-- Insert Sample Data into CelestialItems Table
INSERT INTO CelestialItems (item_name, item_type, discovery_date, celestial_coordinates, description)
VALUES
    ('Stellar Nebula', 'Nebula', '2023-05-15', POINT(45.1234,-120.5678), 'Vast cloud of interstellar gas and dust...'),
    ('Meteorite Fragment', 'Meteorite', '2023-07-02', POINT(12.3456,-78.9012), 'Fragment from an extraterrestrial object...'),
    ('Exoplanet', 'Planet', '2023-08-20', POINT(10.9876,-45.6789), 'Planet orbiting a distant star, potential candidate...');

-- Insert Sample Data into Researchers Table
INSERT INTO Researchers (full_name, specialization, email)
VALUES
    ('Dr. Aurora Starcrest', 'Astrophysicist', 'aurora.starcrest@cdri.space'),
    ('Dr. Orion Nightsky', 'Astronomer', 'orion.nightsky@cdri.space'),
    ('Dr. Lyra Stellaria', 'Geologist', 'lyra.stellaria@cdri.space');

-- Insert Sample Data into AlienEncounters Table
INSERT INTO AlienEncounters (encounter_date, location_coordinates, description)
VALUES
    ('2023-06-10', POINT(37.7890, -122.4014), 'Strange lights observed in the night sky...'),
    ('2023-07-27', POINT(51.5074, -0.1278), 'Unidentified craft hovering above city...'),
    ('2023-09-15', POINT(-34.6037, -58.3816), 'Witnesses report encounter with beings resembling...');
