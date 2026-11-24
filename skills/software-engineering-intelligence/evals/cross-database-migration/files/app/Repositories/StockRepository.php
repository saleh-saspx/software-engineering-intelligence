<?php

namespace App\Repositories;

use Illuminate\Support\Facades\DB;

class StockRepository
{
    public function add(int $warehouseId, string $sku, int $qty): void
    {
        DB::statement(
            'INSERT INTO stock_levels (warehouse_id, sku, quantity) VALUES (?, ?, ?)
             ON DUPLICATE KEY UPDATE quantity = quantity + VALUES(quantity)',
            [$warehouseId, $sku, $qty]
        );
    }

    public function lowStock(): array
    {
        return DB::select('SELECT `sku`, warehouse_id, IFNULL(quantity, 0) AS qty FROM stock_levels WHERE quantity < 5 LIMIT 0, 100');
    }
}
