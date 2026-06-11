-- Schéma minimal pour les tests CI (sans données, sans PostGIS, sans ref_countries)
-- Utilisé par le workflow GitHub Actions

CREATE TABLE IF NOT EXISTS public.localisation (
    code_pays character(2)          NOT NULL,
    nom_pays  character varying(100) NOT NULL,
    ville     character varying(150) NOT NULL,
    CONSTRAINT localisation_pkey PRIMARY KEY (code_pays, ville)
);

CREATE TABLE IF NOT EXISTS public.gare (
    id_gare      character varying(255) NOT NULL,
    nom_officiel character varying(200) NOT NULL,
    code_pays    character(2)           NOT NULL,
    type_liaison character varying(50)  NOT NULL,
    ville        character varying(150) NOT NULL,
    latitude     numeric(9,6),
    longitude    numeric(9,6),
    CONSTRAINT gare_pkey PRIMARY KEY (id_gare),
    CONSTRAINT gare_type_liaison_check CHECK (
        type_liaison IN ('nationale','internationale','régionale')
    ),
    CONSTRAINT gare_code_pays_ville_fkey
        FOREIGN KEY (code_pays, ville)
        REFERENCES public.localisation(code_pays, ville)
        ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS public.operateur (
    id_operateur character varying(255) NOT NULL,
    nom          character varying(200) NOT NULL,
    CONSTRAINT operateur_pkey    PRIMARY KEY (id_operateur),
    CONSTRAINT operateur_nom_key UNIQUE (nom)
);

CREATE TABLE IF NOT EXISTS public.ligne (
    id_ligne  character varying(255) NOT NULL,
    nom_ligne character varying(200) NOT NULL,
    CONSTRAINT ligne_pkey PRIMARY KEY (id_ligne)
);

CREATE TABLE IF NOT EXISTS public.trajet (
    id_trajet        character varying(255) NOT NULL,
    id_service       character varying(255) NOT NULL,
    id_trajet_source character varying(100),
    heure_depart     time without time zone NOT NULL,
    heure_arrivee    time without time zone NOT NULL,
    duree_minutes    integer                NOT NULL,
    id_ligne         character varying(255),
    emission_co2_kg  numeric(10,2),
    id_gare_depart   character varying(255),
    id_gare_arrivee  character varying(255),
    id_operateur     character varying(255),
    CONSTRAINT trajet_pkey PRIMARY KEY (id_trajet)
);

CREATE TABLE IF NOT EXISTS public.historique_import (
    id_import           serial         NOT NULL,
    date_import         timestamp      NOT NULL DEFAULT now(),
    nb_lignes_importees integer        NOT NULL,
    statut              character varying(20) NOT NULL,
    message             text,
    CONSTRAINT historique_import_pkey PRIMARY KEY (id_import),
    CONSTRAINT historique_import_nb_check  CHECK (nb_lignes_importees >= 0),
    CONSTRAINT historique_import_statut_check CHECK (
        statut IN ('succès','echec','partiel')
    )
);

CREATE INDEX IF NOT EXISTS idx_gare_pays       ON public.gare              (code_pays);
CREATE INDEX IF NOT EXISTS idx_historique_date ON public.historique_import (date_import);
CREATE INDEX IF NOT EXISTS idx_trajet_service  ON public.trajet             (id_service);
