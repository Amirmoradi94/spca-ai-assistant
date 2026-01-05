for animal scraping, use following urls:
[https://www.spca.com/en/adoption/cats-for-adoption/](https://www.spca.com/en/adoption/cats-for-adoption/)
[https://www.spca.com/en/adoption/dogs-for-adoption/](https://www.spca.com/en/adoption/dogs-for-adoption/)
[https://www.spca.com/en/adoption/rabbits-for-adoption/](https://www.spca.com/en/adoption/rabbits-for-adoption/)
[https://www.spca.com/en/adoption/birds-for-adoption/](https://www.spca.com/en/adoption/birds-for-adoption/)
[https://www.spca.com/en/adoption/small-animals-for-adoption/](https://www.spca.com/en/adoption/small-animals-for-adoption/)

then in each url, under div class="row pet--row", find all pet cards:
<div class="col-12 col-sm-6 col-md-4 col-lg-3 single--card pet--card order-1">
    	
    
    <a href="https://www.spca.com/en/animal/logan-dog-2000064570/" class="card--link" rel="nofollow" style="position: relative;">
                <div class="card--image">
            <div class="bg-card-image" style="background-image: url('https://g.petango.com/photos/2260/948d9c27-4a70-4117-9712-dc2ef0c52016.jpg');"></div>
            <img src="https://g.petango.com/photos/2260/948d9c27-4a70-4117-9712-dc2ef0c52016.jpg" alt="Logan" title="Logan">
        </div>
        <div class="card--content">
            <h5 class="card--title">Logan</h5>
            <div class="pet--infos">
                Dog ● Young ● Male ● L            </div>
            <div class="btn--link-rounded text-right">
                <span class="btn-round btn-rotate"><i class="icon-cross" aria-hidden="true"></i></span>
            </div>
        </div>
    </a>
</div>

then after extracting url of each pet page:
find class row under class single-pet with this element to extract all info:
<div class="row">
                            <div class="col-12 col-md-6 pet--images pet-single-column">

                                <img src="https://g.petango.com/photos/2260/9d9c438a-c7bc-4c26-ab03-2d15ab443fb4.jpg" alt="" class="rollover-parent">

                                <div class="pet--thumbnails rollover--thumbnails">
                                                                                                                    
                                                                                    <div class="pet--thumbnail rollover--thumbnail">
                                                <img src="https://g.petango.com/photos/2260/2dc8e77b-7962-4e57-b3d4-6e2f931157a1.jpg" alt="Photo 1" class="rollover">
                                            </div>
                                                                                                                                                            
                                                                                    <div class="pet--thumbnail rollover--thumbnail">
                                                <img src="https://g.petango.com/photos/2260/e6516931-3aea-4fb4-8b2e-10d590ef61f4.jpg" alt="Photo 2" class="rollover">
                                            </div>
                                                                                                                                                            
                                                                                    <div class="pet--thumbnail rollover--thumbnail">
                                                <img src="https://g.petango.com/photos/2260/9d9c438a-c7bc-4c26-ab03-2d15ab443fb4.jpg" alt="Photo 3" class="rollover pet--thumbnail-current">
                                            </div>
                                                                                                            </div>
                                
                                                            </div>
                            <div class="col-12 col-md-6 pet-single-column">
                                <h2>Happy</h2>
                                
                                                                    <p>
                                        <b>To meet the animals up for adoption, please come during our <a href="#top">opening hours</a>.</b><br>
                                                                            </p>
                                                                    
                                                                
                                                                
                                                                
                                
                                
                                                                    <h5>Description</h5>
                                    <p>Happy - 2000258404<br><br>Âge / Age : 2 ans / 2 years-old<br>Mâle / Male<br>Race (s) / Breed (s) : Mix<br>Poids / Weight : 30 kg<br><br>Happy porte bien son nom : c'est un chien joyeux, dynamique et toujours prêt pour une nouvelle aventure.<br>Il rêve d'une famille sportive qui aime bouger autant que lui et qui apprécie les randonnées au grand air.<br><br>Explorateur dans l'âme, Happy adore partir en escapade dans la forêt, courir librement et dépenser toute son énergie.<br><br>Il raffole des longues balades, mais lorsqu'il a envie, il sait offrir aussi de beaux câlins.<br><br>Un compagnon actif, attachant et plein de joie, prêt à partager votre vie et vos aventures.</p>
                                

                                <table>
                                    <tbody><tr>
                                        <td class="column_name">Reference Number</td>
                                        <td>2000258404</td>
                                    </tr>
                                    <tr>
                                        <td class="column_name">Species</td>
                                        <td>Dog</td>
                                    </tr>
                                    <tr>
                                        <td class="column_name">Age</td>
                                        <td>2</td>
                                    </tr>
                                    <tr>
                                        <td class="column_name">Sex</td>
                                        <td>Male</td>
                                    </tr>
                                    <tr>
                                        <td class="column_name">Breed</td>
                                        <td>Mixed Breed, Medium (up to 44 lbs fully grown)</td>
                                    </tr>
                                    <tr>
                                        <td class="column_name">Size</td>
                                        <td>M</td>
                                    </tr>
                                    <tr>
                                        <td class="column_name">Color</td>
                                        <td>Black</td>
                                    </tr>
                                    <tr style="display:none;">
                                        <td class="column_name">Declawed</td>
                                        <td>No</td>
                                    </tr>

                                </tbody></table>
                            </div>
                        </div>