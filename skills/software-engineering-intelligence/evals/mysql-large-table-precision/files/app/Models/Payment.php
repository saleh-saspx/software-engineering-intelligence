<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Payment extends Model
{
    protected $casts = [
        'amount' => 'decimal:2',
        'card_expires_at' => 'datetime',
    ];
}
