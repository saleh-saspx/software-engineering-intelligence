# payments-api (Laravel 11)

Production: MySQL 8.0 (InnoDB), one primary and two read replicas (reporting). `payments` has about
80 million rows and receives ~150 writes per second at peak; Friday night traffic is ~20/s.
