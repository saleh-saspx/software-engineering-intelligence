<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up(): void
    {
        Schema::table('payments', function (Blueprint $table) {
            $table->decimal('amount', 19, 4)->change();          // was decimal(10,2)
            $table->timestamp('card_expires_at')->nullable();    // card expiry, e.g. 2031-08-31
            $table->index(['merchant_id', 'created_at']);
        });
    }

    public function down(): void
    {
        Schema::table('payments', function (Blueprint $table) {
            $table->decimal('amount', 10, 2)->change();
            $table->dropColumn('card_expires_at');
            $table->dropIndex(['merchant_id', 'created_at']);
        });
    }
};
