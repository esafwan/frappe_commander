### Commander - Canteen Token Management System

A comprehensive digital token management system for canteen operations, built on Frappe Framework. This system digitizes traditional canteen tokens, enabling efficient tracking, management, and reporting of canteen transactions.

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch develop
bench install-app commander
```

## Features

### Core Functionality
- **Digital Token Management**: Replace physical tokens with digital counterparts
- **Customer Management**: Track canteen users and their token balances
- **Transaction Processing**: Handle token purchases, redemptions, and refunds
- **Menu Management**: Maintain canteen menu items with pricing
- **Reporting & Analytics**: Generate comprehensive reports on usage and revenue

### Key Components
- **Token System**: Digital tokens with unique identifiers and values
- **Customer Accounts**: User profiles with balance tracking and transaction history
- **Menu Items**: Configurable food/beverage items with pricing
- **Transaction Records**: Complete audit trail of all token activities
- **Reporting Dashboard**: Real-time insights and analytics

## System Architecture

### DocTypes Overview

1. **Canteen Customer**: Manages customer information and token balances
2. **Canteen Token**: Individual digital tokens with denominations
3. **Canteen Menu Item**: Food/beverage items available for purchase
4. **Canteen Transaction**: Records all token-related transactions
5. **Canteen Token Purchase**: Handles token buying transactions
6. **Canteen Token Redemption**: Manages token usage for purchases

### Workflow
1. **Customer Registration**: New customers are registered in the system
2. **Token Purchase**: Customers buy digital tokens (cash to tokens)
3. **Menu Ordering**: Customers use tokens to purchase menu items
4. **Transaction Recording**: All activities are logged for audit purposes
5. **Balance Management**: Real-time tracking of customer token balances
6. **Reporting**: Generate insights on usage patterns and revenue

## Usage Examples

### Customer Management
- Register new canteen users
- Track individual token balances
- View transaction history
- Manage customer profiles

### Token Operations
- Issue tokens of various denominations
- Process token purchases with cash payments
- Handle token redemptions for menu items
- Manage token refunds and adjustments

### Menu Management
- Add/update menu items with prices
- Set availability status
- Track popular items
- Manage seasonal menus

### Reporting
- Daily/weekly/monthly transaction reports
- Customer usage analytics
- Revenue tracking and forecasting
- Token circulation analysis

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/commander
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### License

mit


For adding data use Frappe MCP available to you. 