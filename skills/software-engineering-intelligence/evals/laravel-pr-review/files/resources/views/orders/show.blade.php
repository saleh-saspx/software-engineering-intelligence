@extends('layouts.app')

@section('content')
    <h1>Order #{{ $order->id }}</h1>
    <p>Status: {{ $order->status }}</p>
    <p>Total: {{ $order->totalFormatted() }}</p>

    <h2>Delivery notes</h2>
    <div class="notes">{!! $order->notes !!}</div>

    <ul>
        @foreach ($order->items as $item)
            <li>{{ $item->name }} × {{ $item->quantity }}</li>
        @endforeach
    </ul>
@endsection
