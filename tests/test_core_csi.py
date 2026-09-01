"""Unit tests for CanonicalSymbolId (CSI)."""

from semantic_engine.core.csi import CanonicalSymbolId


def test_csi_parsing_and_formatting():
    uri = "csi://sample_project/services/OrderService.create_order#user_id"
    csi = CanonicalSymbolId.parse(uri)

    assert csi.package == "sample_project"
    assert csi.namespace == ("services",)
    assert csi.symbol_name == "OrderService"
    assert csi.member_path == ("create_order",)
    assert csi.fragment == "user_id"
    assert str(csi) == uri
    assert csi.qualified_name == "sample_project.services.OrderService.create_order"


def test_csi_parent_and_children():
    method_csi = CanonicalSymbolId.parse("csi://sample_project/services/OrderService.create_order")
    class_csi = CanonicalSymbolId.parse("csi://sample_project/services/OrderService")
    param_csi = method_csi.with_fragment("user_id")

    assert param_csi.parent_csi == method_csi
    assert method_csi.parent_csi == class_csi
    assert class_csi.child("create_order") == method_csi
    assert method_csi.is_descendant_of(class_csi)


def test_csi_overload_parsing_and_formatting():
    # Multi-parameter overload
    uri1 = "csi://com.example.store/services/OrderService.findOrders(String,int)"
    csi1 = CanonicalSymbolId.parse(uri1)
    assert csi1.package == "com.example.store"
    assert csi1.namespace == ("services",)
    assert csi1.symbol_name == "OrderService"
    assert csi1.member_path == ("findOrders",)
    assert csi1.signature_spec == ("String", "int")
    assert str(csi1) == uri1
    assert csi1.qualified_name == "com.example.store.services.OrderService.findOrders(String,int)"

    # Single-parameter overload with fragment
    uri2 = "csi://com.example.store/services/OrderService.findOrders(UUID)#id_param"
    csi2 = CanonicalSymbolId.parse(uri2)
    assert csi2.signature_spec == ("UUID",)
    assert csi2.fragment == "id_param"
    assert str(csi2) == uri2

    # Zero-parameter overload
    uri3 = "csi://com.example.store/services/OrderService.findOrders()"
    csi3 = CanonicalSymbolId.parse(uri3)
    assert csi3.signature_spec == ()
    assert str(csi3) == uri3


def test_csi_overload_hierarchy_and_lineage():
    csi_frag = CanonicalSymbolId.parse("csi://com.example.store/services/OrderService.findOrders(String,int)#p1")
    csi_overload = CanonicalSymbolId.parse("csi://com.example.store/services/OrderService.findOrders(String,int)")
    csi_bare_group = CanonicalSymbolId.parse("csi://com.example.store/services/OrderService.findOrders")
    csi_class = CanonicalSymbolId.parse("csi://com.example.store/services/OrderService")

    # Parent chain
    assert csi_frag.parent_csi == csi_overload
    assert csi_overload.parent_csi == csi_bare_group
    assert csi_bare_group.parent_csi == csi_class

    # Helpers
    assert csi_bare_group.with_signature("String,int") == csi_overload
    assert csi_overload.without_signature() == csi_bare_group

    # Descendants
    assert csi_overload.is_descendant_of(csi_bare_group)
    assert csi_overload.is_descendant_of(csi_class)
    assert csi_frag.is_descendant_of(csi_overload)

