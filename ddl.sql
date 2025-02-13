CREATE TABLE product_update_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    email VARCHAR(255) NOT NULL,
    product_id VARCHAR NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    changes_summary TEXT,
    CONSTRAINT fk_user
        FOREIGN KEY(user_id)
        REFERENCES "user"(id)
        ON DELETE CASCADE
);

CREATE INDEX idx_product_update_logs_user_id ON product_update_logs(user_id);
CREATE INDEX idx_product_update_logs_product_id ON product_update_logs(product_id);

insert into role values (32, 'reject product', false, false, true, false, 5);
insert into role values (33, 'reject product', false, false, true, false, 4);
insert into role values (34, 'reject product', false, false, true, false, 1);

ALTER TABLE sizes
ADD COLUMN sleeve_length double precision;

ALTER TABLE public.styles
ADD COLUMN colour_intensity character varying;