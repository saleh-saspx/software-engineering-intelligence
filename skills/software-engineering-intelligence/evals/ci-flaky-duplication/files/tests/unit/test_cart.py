import time

from shop.cart import Cart


def test_merge_carts():
    a, b = Cart(items={"x": 1}), Cart(items={"x": 2, "y": 1})
    assert a.merge(b).items == {"x": 3, "y": 1}


def test_expired_cart():
    cart = Cart(items={}, ttl_seconds=2)
    time.sleep(2)
    assert cart.expired
