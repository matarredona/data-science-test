from functions import simulate_data, get_shrinkage_rates, plot_shrinkage_rate, plot_shrinkage_rates_by_sc, plot_pool_size

if __name__ == "__main__":

    data = simulate_data()
    data = get_shrinkage_rates(data)
    print(data)
    plot_shrinkage_rate(data, "figures")
    plot_shrinkage_rates_by_sc(data, "figures")
    plot_pool_size(data, "figures")