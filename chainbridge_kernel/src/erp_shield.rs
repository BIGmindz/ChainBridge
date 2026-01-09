// ============================================================================
// FILE: erp_shield.rs
// CONTEXT: PAC-STRAT-P48-MOAT-ENFORCEMENT (The Invariant Engine)
// AUTH: CODY (GID-02) / BENSON (GID-00)
// PURPOSE: NetSuite ERP Schema Validation - Structural & Semantic Gates
// INVARIANT: No floats, no invalid currencies, no negative amounts
// SECURITY: Fail-Closed - Invalid data is silently rejected
// ============================================================================

use serde::{Deserialize, Serialize};
use std::collections::HashSet;

// ============================================================================
// STRICT SCHEMA DEFINITIONS
// All monetary values are CENTS (i64) - no floating point allowed
// ============================================================================

/// NetSuite Invoice - The canonical financial document structure
/// CRITICAL: totalAmount is in CENTS (multiply dollars by 100)
#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct NetSuiteInvoice {
    /// NetSuite internal ID (must not be empty)
    #[serde(rename = "internalId")]
    pub internal_id: String,
    
    /// Customer/Entity identifier
    #[serde(rename = "entityId")]
    pub entity_id: String,
    
    /// Total amount in CENTS (i64, not float!)
    /// Example: $500.00 = 50000 cents
    #[serde(rename = "totalAmount")]
    pub total_amount: i64,
    
    /// ISO 4217 currency code (USD, EUR, GBP, etc.)
    pub currency: String,
    
    /// NetSuite subsidiary ID
    pub subsidiary: String,
    
    /// Optional line items
    #[serde(rename = "lineItems", default)]
    pub line_items: Vec<InvoiceLineItem>,
    
    /// Optional memo/notes
    #[serde(default)]
    pub memo: Option<String>,
}

/// Individual line item on an invoice
#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct InvoiceLineItem {
    /// Item identifier
    #[serde(rename = "itemId")]
    pub item_id: String,
    
    /// Quantity (must be positive)
    pub quantity: i32,
    
    /// Unit price in CENTS
    #[serde(rename = "unitPrice")]
    pub unit_price: i64,
    
    /// Line total in CENTS (should equal quantity * unitPrice)
    #[serde(rename = "lineTotal")]
    pub line_total: i64,
}

// ============================================================================
// VALIDATION ERROR TYPES
// These are internal - never exposed to external callers
// ============================================================================

#[derive(Debug, Clone)]
pub enum ValidationError {
    /// Empty required field
    EmptyField(&'static str),
    /// Negative monetary value
    NegativeAmount(&'static str),
    /// Invalid currency code
    InvalidCurrency(String),
    /// Invalid subsidiary
    InvalidSubsidiary(String),
    /// Line item math doesn't add up
    LineItemMismatch { item_id: String, expected: i64, actual: i64 },
    /// Total doesn't match line items
    TotalMismatch { expected: i64, actual: i64 },
    /// Quantity must be positive
    InvalidQuantity { item_id: String, quantity: i32 },
}

// ============================================================================
// ALLOWED VALUES (Constitutional Invariants)
// ============================================================================

lazy_static::lazy_static! {
    /// ISO 4217 currency codes we accept
    static ref VALID_CURRENCIES: HashSet<&'static str> = {
        let mut set = HashSet::new();
        set.insert("USD");
        set.insert("EUR");
        set.insert("GBP");
        set.insert("CAD");
        set.insert("AUD");
        set.insert("JPY");
        set.insert("CHF");
        set.insert("CNY");
        set.insert("HKD");
        set.insert("SGD");
        set.insert("MXN");
        set.insert("BRL");
        set
    };
    
    /// Valid subsidiary IDs (configurable per deployment)
    static ref VALID_SUBSIDIARIES: HashSet<&'static str> = {
        let mut set = HashSet::new();
        set.insert("1");      // Parent Company
        set.insert("2");      // US Operations
        set.insert("3");      // EU Operations
        set.insert("4");      // APAC Operations
        set.insert("100");    // Test/Sandbox
        set
    };
}

// ============================================================================
// VALIDATION IMPLEMENTATION
// ============================================================================

impl NetSuiteInvoice {
    /// Validate the invoice against all business rules
    /// Returns Ok(()) if valid, Err(ValidationError) if invalid
    pub fn validate(&self) -> Result<(), ValidationError> {
        // GATE 1: Required fields not empty
        if self.internal_id.trim().is_empty() {
            return Err(ValidationError::EmptyField("internalId"));
        }
        if self.entity_id.trim().is_empty() {
            return Err(ValidationError::EmptyField("entityId"));
        }
        if self.subsidiary.trim().is_empty() {
            return Err(ValidationError::EmptyField("subsidiary"));
        }
        
        // GATE 2: No negative amounts
        if self.total_amount < 0 {
            return Err(ValidationError::NegativeAmount("totalAmount"));
        }
        
        // GATE 3: Valid currency code (ISO 4217)
        if !VALID_CURRENCIES.contains(self.currency.as_str()) {
            return Err(ValidationError::InvalidCurrency(self.currency.clone()));
        }
        
        // GATE 4: Valid subsidiary
        if !VALID_SUBSIDIARIES.contains(self.subsidiary.as_str()) {
            return Err(ValidationError::InvalidSubsidiary(self.subsidiary.clone()));
        }
        
        // GATE 5: Validate line items if present
        let mut calculated_total: i64 = 0;
        for item in &self.line_items {
            item.validate()?;
            calculated_total += item.line_total;
        }
        
        // GATE 6: If line items exist, total must match
        if !self.line_items.is_empty() && calculated_total != self.total_amount {
            return Err(ValidationError::TotalMismatch {
                expected: calculated_total,
                actual: self.total_amount,
            });
        }
        
        Ok(())
    }
}

impl InvoiceLineItem {
    /// Validate a single line item
    pub fn validate(&self) -> Result<(), ValidationError> {
        // Quantity must be positive
        if self.quantity <= 0 {
            return Err(ValidationError::InvalidQuantity {
                item_id: self.item_id.clone(),
                quantity: self.quantity,
            });
        }
        
        // Unit price must not be negative
        if self.unit_price < 0 {
            return Err(ValidationError::NegativeAmount("unitPrice"));
        }
        
        // Line total must not be negative
        if self.line_total < 0 {
            return Err(ValidationError::NegativeAmount("lineTotal"));
        }
        
        // Math check: line_total should equal quantity * unit_price
        let expected = (self.quantity as i64) * self.unit_price;
        if expected != self.line_total {
            return Err(ValidationError::LineItemMismatch {
                item_id: self.item_id.clone(),
                expected,
                actual: self.line_total,
            });
        }
        
        Ok(())
    }
}

// ============================================================================
// UNIT TESTS - Prove the invariants hold
// ============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    fn valid_invoice() -> NetSuiteInvoice {
        NetSuiteInvoice {
            internal_id: "INV-001".to_string(),
            entity_id: "CUST-001".to_string(),
            total_amount: 50000, // $500.00 in cents
            currency: "USD".to_string(),
            subsidiary: "1".to_string(),
            line_items: vec![],
            memo: None,
        }
    }

    #[test]
    fn test_valid_invoice_passes() {
        let invoice = valid_invoice();
        assert!(invoice.validate().is_ok());
    }

    #[test]
    fn test_empty_internal_id_fails() {
        let mut invoice = valid_invoice();
        invoice.internal_id = "".to_string();
        assert!(matches!(
            invoice.validate(),
            Err(ValidationError::EmptyField("internalId"))
        ));
    }

    #[test]
    fn test_negative_amount_fails() {
        let mut invoice = valid_invoice();
        invoice.total_amount = -100;
        assert!(matches!(
            invoice.validate(),
            Err(ValidationError::NegativeAmount("totalAmount"))
        ));
    }

    #[test]
    fn test_invalid_currency_fails() {
        let mut invoice = valid_invoice();
        invoice.currency = "FAKE".to_string();
        assert!(matches!(
            invoice.validate(),
            Err(ValidationError::InvalidCurrency(_))
        ));
    }

    #[test]
    fn test_invalid_subsidiary_fails() {
        let mut invoice = valid_invoice();
        invoice.subsidiary = "999".to_string();
        assert!(matches!(
            invoice.validate(),
            Err(ValidationError::InvalidSubsidiary(_))
        ));
    }

    #[test]
    fn test_line_items_math_check() {
        let mut invoice = valid_invoice();
        invoice.total_amount = 10000; // $100.00
        invoice.line_items = vec![
            InvoiceLineItem {
                item_id: "ITEM-001".to_string(),
                quantity: 2,
                unit_price: 5000, // $50.00 each
                line_total: 10000, // $100.00 total
            }
        ];
        assert!(invoice.validate().is_ok());
    }

    #[test]
    fn test_line_items_total_mismatch_fails() {
        let mut invoice = valid_invoice();
        invoice.total_amount = 99999; // Wrong total
        invoice.line_items = vec![
            InvoiceLineItem {
                item_id: "ITEM-001".to_string(),
                quantity: 2,
                unit_price: 5000,
                line_total: 10000,
            }
        ];
        assert!(matches!(
            invoice.validate(),
            Err(ValidationError::TotalMismatch { .. })
        ));
    }

    #[test]
    fn test_line_item_math_mismatch_fails() {
        let mut invoice = valid_invoice();
        invoice.total_amount = 10000;
        invoice.line_items = vec![
            InvoiceLineItem {
                item_id: "ITEM-001".to_string(),
                quantity: 2,
                unit_price: 5000,
                line_total: 9999, // Wrong! Should be 10000
            }
        ];
        assert!(matches!(
            invoice.validate(),
            Err(ValidationError::LineItemMismatch { .. })
        ));
    }
}
