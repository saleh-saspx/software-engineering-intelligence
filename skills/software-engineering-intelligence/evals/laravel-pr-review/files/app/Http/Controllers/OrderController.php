<?php

namespace App\Http\Controllers;

use App\Models\Order;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Log;

class OrderController extends Controller
{
    public function index(Request $request)
    {
        $orders = Cache::remember('orders.customer.' . $request->user()->id, 60, function () use ($request) {
            return Order::forCustomer($request->user()->id)
                ->with('items')
                ->latest('placed_at')
                ->paginate(20);
        });

        return view('orders.index', ['orders' => $orders]);
    }

    public function show($id)
    {
        $order = Order::with('items')->findOrFail($id);

        return view('orders.show', ['order' => $order]);
    }

    public function search(Request $request)
    {
        $status = $request->input('status', 'open');
        $sort = $request->input('sort', 'placed_at');

        $orders = DB::select(
            "SELECT * FROM orders WHERE customer_id = " . $request->user()->id .
            " AND status = '$status' ORDER BY $sort DESC"
        );

        return view('orders.index', ['orders' => $orders]);
    }

    public function export()
    {
        $rows = [];
        foreach (Order::all() as $order) {
            $rows[] = [
                $order->id,
                $order->customer->name,
                $order->customer->email,
                $order->status,
                $order->totalFormatted(),
            ];
        }

        Log::info('orders exported', ['count' => count($rows)]);

        $csv = fopen('php://temp', 'r+');
        foreach ($rows as $row) {
            fputcsv($csv, $row);
        }
        rewind($csv);

        return response(stream_get_contents($csv), 200, [
            'Content-Type' => 'text/csv',
            'Content-Disposition' => 'attachment; filename="orders.csv"',
        ]);
    }

    public function update(Request $request, $id)
    {
        $order = Order::findOrFail($id);

        $request->validate([
            'notes' => 'nullable|string|max:2000',
            'shipping_address' => 'nullable|string|max:500',
        ]);

        $order->update($request->all());

        return redirect()->route('orders.show', $order->id);
    }
}
