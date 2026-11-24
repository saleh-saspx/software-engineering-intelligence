<?php
return [
    'default' => env('DB_CONNECTION', 'mysql'),
    'connections' => [
        'mysql' => [
            'driver' => 'mysql',
            'host' => env('DB_HOST'),
            'database' => env('DB_DATABASE'),
            'charset' => 'utf8mb4',
            'collation' => 'utf8mb4_0900_ai_ci',
        ],
    ],
];
