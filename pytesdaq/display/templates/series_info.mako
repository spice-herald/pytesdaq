 <html lang="en"><head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    <meta name="description" content="">
    <meta name="author" content="Mark Otto, Jacob Thornton, and Bootstrap contributors">
    <meta name="generator" content="Jekyll v4.0.1">
    <title>Series Info – TES</title>

  
    <style>
      .bd-placeholder-img {
        font-size: 2rem;
        text-anchor: left;
        -webkit-user-select: none;
        -moz-user-select: none;
        -ms-user-select: none;
        user-select: none;
      }

      body {
      padding-top: 90px;
    }
    .table-border {
        padding: 10px;  
        border-collapse: collapse;      
      }

      @media (min-width: 768px) {
        .bd-placeholder-img-lg {
          font-size: 4.5rem;≤
        }
      }
    </style>
    <!-- Custom styles for this template -->
    <link href="/static/css/bootstrap.min.css" rel="stylesheet">

  </head>

  <%include file="/header.mako" /> 
  <body>
  

<main role="main" class="container">

    <h2>Series Info for ${this_series['series_num']}</h2>
    <h3> In group <a  href="/group/${this_series['group_name']}">${this_series['group_name']}</a></h3>

  <div>
     <table id="series_table" class="table table-hover table-sm table-responsive table-bordered table-striped" style="font-size: 0.8rem;">
            <tbody>
              % for s in this_series:
                <tr id="${s}">
                  <td>${s}</td>
                  <td>${this_series[s]}</td>
                </tr>
              % endfor
            </tbody>
          </table>
  </div>

</main><!-- /.container -->
<script src="https://code.jquery.com/jquery-3.5.1.slim.min.js" integrity="sha384-DfXdz2htPH0lsSSs5nCTpuj/zy4C+OGpamoFVy38MVBnE+IbbVYUew+OrCXaRkfj" crossorigin="anonymous"></script>
<script>window.jQuery || document.write('<script src="/docs/4.4/assets/js/vendor/jquery.slim.min.js"><\/script>') </script> <script src="/static/js/bootstrap.bundle.min.js"></script>

</body></html>
