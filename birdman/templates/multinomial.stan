data {
  int<lower=0> N;       // number of samples
  int<lower=0> D;       // number of dimensions
  int<lower=0> p;       // number of covariates
  real depth[N];        // sequencing depths of microbes
  matrix[N, p] x;       // covariate matrix
  int y[N, D];          // observed microbe abundances
  real<lower=0> B_p;    // stdev for Beta Normal prior
}

parameters {
  // parameters required for linear regression on the species means
  matrix[p, D-1] beta;
}

transformed parameters {
  matrix[N, D-1] lam;
  matrix[N, D] lam_clr;
  vector[N] z;
  simplex[D] theta[N];

  z = to_vector(rep_array(0, N));
  lam = x * beta;
  lam_clr = append_col(z, lam);
  for (n in 1:N){
    theta[n] = softmax(to_vector(lam_clr[n,]));
  }
}

model {
  // setting priors ...
  for (i in 1:D-1){
    for (j in 1:p){
      beta[j, i] ~ normal(0., B_p); // uninformed prior
    }
  }
  // generating counts
  for (n in 1:N){
    target += multinomial_lpmf(y[n,] | to_vector(theta[n,]));
  }
}
